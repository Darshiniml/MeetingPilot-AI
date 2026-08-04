"""Comprehensive test suite for Phase 7.2 long-term memory system."""

import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.memory.memory_models import Memory
from app.memory.memory_repository import MemoryRepository
from app.memory.vector_store import SQLiteVectorStore, MockVectorStore, cosine_similarity
from app.memory.embedding_service import CachedEmbeddingService
from app.memory.memory_retriever import MemoryRetriever
from app.memory.memory_ranker import MemoryRanker
from app.memory.memory_compactor import MemoryCompactor
from app.memory.memory_manager import MemoryManager, get_memory_manager
from app.memory.memory_indexer import MemoryIndexer
from app.agent.events.event_bus import EventBus
from app.agent.events.event_models import SummaryGeneratedEvent, TranscriptSavedEvent
from app.agent.events.event_types import EventType
from app.agent.planner import Planner
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.agent_context import AgentContext
from app.models.user import User
from app.models.meeting import Meeting
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.registry import ToolRegistry
from app.agent.models import AgentRequest, ExecutionPlan, ToolExecution
from app.agent.reflection import ReflectionEngine


# In-memory SQLite database for testing isolation
test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=test_engine)


class MockEmbeddingClient:
    """Mock of the core local embedding client for stable tests."""
    def embed_texts(self, texts):
        # Deterministic embeddings: return [0.5, 0.5, ...] or simple hashes
        return [[float(hash(t) % 100) / 100.0] * 1536 for t in texts]


class MockLLMProvider:
    """Mock LLM provider for deterministic memory importance scoring."""
    def generate(self, prompt):
        class LLMResult:
            content = "0.85"
        return LLMResult()


class MemorySystemTests(unittest.TestCase):
    def setUp(self) -> None:
        # Clear database records
        with TestingSessionLocal() as session:
            session.query(Memory).delete()
            session.commit()

        # Initialize mock components
        self.mock_emb_client = MockEmbeddingClient()
        self.mock_llm = MockLLMProvider()

        # Patchers for Ollama calls
        self.patcher_emb = patch("app.memory.embedding_service.get_embedding_service", return_value=self.mock_emb_client)
        self.patcher_llm = patch("app.memory.memory_indexer.get_llm_provider", return_value=self.mock_llm)
        self.patcher_emb.start()
        self.patcher_llm.start()

        # Setup MemoryManager with testing database session factory
        self.mgr = MemoryManager(use_mock_store=False, session_factory=TestingSessionLocal)
        
        # Override singleton
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = self.mgr

    def tearDown(self) -> None:
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = None
        self.patcher_emb.stop()
        self.patcher_llm.stop()

    def test_cosine_similarity(self) -> None:
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)
        self.assertAlmostEqual(cosine_similarity([], v1), 0.0)

    def test_embedding_service_caching_and_retry(self) -> None:
        service = CachedEmbeddingService()
        
        # Verify first call generates via client
        embs1 = service.embed_texts(["hello"])
        self.assertEqual(len(embs1), 1)
        self.assertEqual(service.get_latency_count(), 1)

        # Verify second call retrieves from cache without invoking client
        embs2 = service.embed_texts(["hello"])
        self.assertEqual(embs1, embs2)
        self.assertEqual(service.get_latency_count(), 1) # Count stays 1, cached hit!

    def test_memory_repository_crud(self) -> None:
        with TestingSessionLocal() as session:
            repo = MemoryRepository(session)
            
            # Create
            mem = repo.create_memory(
                memory_id="test-id-1",
                memory_type="PreferenceMemory",
                user_id=1,
                title="Favorite Language",
                content="Python",
                embedding=[0.1] * 1536,
                metadata={"scope": "global"},
                importance_score=0.9
            )
            self.assertEqual(mem.content, "Python")

            # Retrieve
            fetched = repo.get_memory("test-id-1")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.title, "Favorite Language")

            # Update
            repo.update_memory("test-id-1", content="TypeScript", importance_score=0.7)
            self.assertEqual(repo.get_memory("test-id-1").content, "TypeScript")
            self.assertEqual(repo.get_memory("test-id-1").importance_score, 0.7)

            # Access Increment
            repo.increment_access("test-id-1")
            self.assertEqual(repo.get_memory("test-id-1").access_count, 1)

            # Delete
            deleted = repo.delete_memory("test-id-1")
            self.assertTrue(deleted)
            self.assertIsNone(repo.get_memory("test-id-1"))

    def test_vector_stores_search(self) -> None:
        mock_store = MockVectorStore()
        mock_store.add("id-A", [1.0, 0.0, 0.0], user_id=1, memory_type="KnowledgeMemory")
        mock_store.add("id-B", [0.0, 1.0, 0.0], user_id=1, memory_type="KnowledgeMemory")
        
        matches = mock_store.search([1.0, 0.0, 0.0], limit=1, user_id=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["memory_id"], "id-A")

    def test_memory_ranker_composite_score(self) -> None:
        ranker = MemoryRanker(
            sim_weight=1.0,
            recency_weight=0.5,
            importance_weight=0.5,
            freq_weight=0.5,
            relevance_weight=0.5
        )
        
        now = datetime.now(timezone.utc)
        
        # Define candidate memories
        candidates = [
            {
                "memory_id": "A",
                "score": 0.9, # High similarity
                "created_at": now - timedelta(hours=24), # Old
                "importance_score": 0.3,
                "access_count": 0,
                "meeting_id": 1,
            },
            {
                "memory_id": "B",
                "score": 0.5, # Low similarity
                "created_at": now, # Brand new
                "importance_score": 0.9, # High importance
                "access_count": 10, # Frequently accessed
                "meeting_id": 2,
            }
        ]

        # Rank with current meeting context of ID 2
        ranked = ranker.rank(candidates, current_meeting_id=2)
        
        self.assertEqual(len(ranked), 2)
        # B should rank higher due to recency, importance, access frequency, and meeting relevance boosts
        self.assertEqual(ranked[0]["memory_id"], "B")
        self.assertTrue(ranked[0]["composite_score"] > ranked[1]["composite_score"])

    def test_memory_compactor(self) -> None:
        # Insert two highly similar memories
        self.mgr.add_custom_memory(
            user_id=1,
            memory_type="ReflectionMemory",
            title="Reflection A",
            content="Workflow completed successfully with scheduler.",
            metadata={"run": 1}
        )
        self.mgr.add_custom_memory(
            user_id=1,
            memory_type="ReflectionMemory",
            title="Reflection B",
            content="Workflow completed successfully with scheduler.",
            metadata={"run": 2}
        )
        
        # Verify both exist
        with TestingSessionLocal() as session:
            initial_count = session.query(Memory).count()
            self.assertEqual(initial_count, 2)

        # Run compaction
        savings = self.mgr.compact_memories(user_id=1)
        self.assertEqual(savings, 1)

        # Verify one is remaining and metadata is combined
        with TestingSessionLocal() as session:
            final_count = session.query(Memory).count()
            self.assertEqual(final_count, 1)
            remaining = session.query(Memory).first()
            meta = json.loads(remaining.metadata_json)
            self.assertIn("run", meta)

    def test_memory_indexer_event_bus_hook(self) -> None:
        bus = EventBus()
        # The memory package hooks publish dynamically on import.
        # Verify that publishing an event on EventBus creates a database record
        event = SummaryGeneratedEvent(
            user_id=1,
            meeting_id=5,
            payload={"summary": "This meeting was about scheduling reviews."}
        )
        
        bus.publish(event)

        # Query database to assert memory was indexed
        with TestingSessionLocal() as session:
            mems = session.query(Memory).all()
            self.assertEqual(len(mems), 1)
            self.assertEqual(mems[0].meeting_id, 5)
            self.assertEqual(mems[0].memory_type, "MeetingMemory")
            self.assertIn("scheduling reviews", mems[0].content)

    def test_planner_memory_context_injection(self) -> None:
        # Clear database and vector store for isolation
        with TestingSessionLocal() as session:
            session.query(Memory).delete()
            session.commit()
        self.mgr.vector_store.clear()
        
        # Seed memories
        self.mgr.add_custom_memory(user_id=1, memory_type="KnowledgeMemory", title="Insight", content="Rahul prefers morning status reviews.")

        planner = Planner()
        # Mock LLM provider to capture prompt arguments
        planner._provider = MagicMock()
        planner._provider.generate.return_value = type("Res", (), {"content": '{"intent":"GENERAL_CHAT","confidence":0.9,"tools":[],"parameters":{},"reasoning":"completed review proposal"}'})()

        # Execute planning request
        planner.plan("Schedule review meeting with Rahul")

        # Verify call context contains long term memory key
        args = planner._provider.generate.call_args[0][0]
        self.assertIn("long_term_memory", args)
        self.assertIn("Rahul prefers morning status reviews", args)

    def test_supervisor_memory_pre_fetch(self) -> None:
        # Seed memory
        self.mgr.add_custom_memory(user_id=1, memory_type="PreferenceMemory", title="Timeline", content="Acme review deadline is Thursday.")

        tools = ToolRegistry()
        for name in ("contacts", "scheduler", "calendar", "gmail", "summary", "transcript", "meeting_history", "action_items", "rag_chat"):
            tools.register(name, lambda *, context, _name=name, **_params: {"tool": _name, "user": context.current_user})
        
        context = AgentContext(tool_registry=tools, reasoning_engine=ReasoningEngine(tools))
        from app.agents.agent_registry import AgentRegistry
        registry = AgentRegistry(context, auto_register=False)
        
        # Register a dummy research agent to prevent KeyError
        from app.agents.base_agent import BaseAgent, AgentResult
        class DummyResearchAgent(BaseAgent):
            def name(self): return "research"
            def description(self): return "dummy research"
            def execute(self, request): return AgentResult("research", "ok")
        registry.register(DummyResearchAgent(context))
        
        supervisor = SupervisorAgent(context, registry)

        req = AgentRequest(user_message="Schedule review for Acme Corp", user_id=1, conversation_id="c-test")
        
        # Monkeypatched handle executes pre-fetch memory retrieval
        supervisor.handle(req)

        working = context.conversation_store.get_working_memory("c-test")
        self.assertIn("long_term_memory", working.tool_outputs)
        self.assertIn("Acme review deadline is Thursday", str(working.tool_outputs["long_term_memory"]))

    def test_reflection_auto_indexing(self) -> None:
        engine = ReflectionEngine()
        
        from app.agent.models import AgentIntent
        plan = ExecutionPlan(intent=AgentIntent.GENERAL_CHAT, confidence=1.0, tools=["contacts", "calendar"], parameters={}, reasoning="Schedule review flow")
        executions = [
            ToolExecution(tool_name="contacts", status="completed", execution_time_ms=10, output="Found Rahul"),
            ToolExecution(tool_name="calendar", status="completed", execution_time_ms=20, output="Event created"),
        ]

        # Trigger reflection
        engine.reflect(plan, executions)

        # Check DB to verify reflection memory was created
        with TestingSessionLocal() as session:
            refls = session.query(Memory).filter(Memory.memory_type == "ReflectionMemory").all()
            self.assertEqual(len(refls), 1)
            self.assertIn("Plan intent: GENERAL_CHAT", refls[0].content)
            self.assertIn("contacts", refls[0].content)
            self.assertIn("calendar", refls[0].content)


if __name__ == "__main__":
    unittest.main()
