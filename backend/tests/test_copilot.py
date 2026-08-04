"""Comprehensive test suite for Phase 7.3 Live Copilot and real-time intelligence."""

import json
import unittest
from typing import Any
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.user import User
from app.models.meeting import Meeting
from app.memory.memory_models import Memory

from app.agent.events.event_bus import EventBus
from app.agent.events.event_models import TranscriptSavedEvent, MeetingStartedEvent
from app.agent.events.event_types import EventType
from app.copilot.copilot_models import LiveMeetingState, CopilotInsight
from app.copilot.copilot_service import get_live_copilot_service, get_copilot_socket_manager
from app.copilot.decision_detector import DecisionDetector
from app.copilot.risk_detector import RiskDetector
from app.copilot.deadline_detector import DeadlineDetector
from app.copilot.question_detector import QuestionDetector
from app.copilot.commitment_detector import CommitmentDetector
from app.copilot.engagement_analyzer import EngagementAnalyzer
from app.copilot.recommendation_engine import RecommendationEngine
from app.agent.planner import Planner
from app.agent.models import AgentIntent


# isolated testing DB
test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=test_engine)


class MockEmbeddingClient:
    def embed_texts(self, texts):
        return [[0.5] * 1536 for t in texts]


class MockLLMProvider:
    """Mock LLM Provider returning static JSON or clean strings."""
    def generate(self, prompt: str) -> Any:
        class Res:
            if "JSON" in prompt or "owner" in prompt:
                content = '{"task": "Finalize client pitch", "owner": "Rahul", "deadline": "Friday afternoon"}'
            elif "scale of 0.0 to 1.0" in prompt:
                content = "0.85"
            elif "Refine" in prompt or "decision" in prompt:
                content = "We decided to restructure the database schema."
            else:
                content = '{"intent":"GENERAL_CHAT","confidence":0.9,"tools":[],"parameters":{},"reasoning":"general response"}'
        return Res()


class CopilotSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        # Clear testing database
        with TestingSessionLocal() as session:
            session.query(Memory).delete()
            session.commit()

        # Setup MemoryManager with testing database session factory
        from app.memory.memory_manager import MemoryManager
        self.mgr = MemoryManager(use_mock_store=False, session_factory=TestingSessionLocal)
        
        # Override singleton
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = self.mgr

        # Mocks
        self.mock_emb = MockEmbeddingClient()
        self.mock_llm = MockLLMProvider()

        self.patchers = [
            patch("app.memory.embedding_service.get_embedding_service", return_value=self.mock_emb),
            patch("app.copilot.decision_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.copilot.risk_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.copilot.deadline_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.memory.memory_indexer.get_llm_provider", return_value=self.mock_llm),
            patch("app.ai.providers.get_llm_provider", return_value=self.mock_llm),
        ]
        for p in self.patchers:
            p.start()

        # Get live copilot service and clear previous states/metrics
        self.service = get_live_copilot_service()
        self.service._states.clear()
        self.service.metrics = {
            "insights_generated": 0,
            "recommendations": 0,
            "decisions": 0,
            "risks": 0,
            "questions": 0,
            "commitments": 0,
            "average_latency_ms": 0.0,
            "processing_count": 0,
        }

    def tearDown(self) -> None:
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = None
        for p in self.patchers:
            p.stop()

    def test_decision_detector(self) -> None:
        detector = DecisionDetector()
        
        # Test heuristic matching
        res = detector.detect("We decided to restructure the database schema.", speaker="Alice")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["speaker"], "Alice")
        self.assertIn("restructure the database", res[0]["content"])

    def test_risk_detector(self) -> None:
        detector = RiskDetector()
        
        # High Severity Blocker
        res = detector.detect("The deployment is completely blocked by authentication failures.", speaker="Bob")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["metadata"]["severity"], "high")
        self.assertEqual(res[0]["metadata"]["category"], "Blocked Work")

        # Medium Severity Dependency
        res2 = detector.detect("We are waiting for the API specs to be finalized.", speaker="Bob")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["metadata"]["severity"], "medium")

    def test_deadline_detector(self) -> None:
        detector = DeadlineDetector()
        
        res = detector.detect("Rahul will complete the client pitch by Friday afternoon.", speaker="Rahul")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["metadata"]["owner"], "Rahul")
        self.assertEqual(res[0]["metadata"]["deadline"], "Friday afternoon")

    def test_question_detector_and_resolution(self) -> None:
        detector = QuestionDetector()
        
        # Detect question
        res = detector.detect("What is the release date?", speaker="Alice")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["metadata"]["question_text"], "What is the release date?")

        # Check resolution
        open_qs = ["What is the release date?"]
        resolved = detector.check_resolution("that answers it, thank you", open_qs)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0], "What is the release date?")

    def test_commitment_detector(self) -> None:
        detector = CommitmentDetector()
        
        res = detector.detect("I'll send the updated dashboard mock tonight.", speaker="Bob")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["metadata"]["action_verb"], "send")
        self.assertIn("dashboard mock tonight", res[0]["metadata"]["action_detail"])

    def test_engagement_analyzer(self) -> None:
        analyzer = EngagementAnalyzer()
        
        speaking_times = {"Alice": 120.0, "Bob": 80.0, "Charlie": 0.0}
        participants = ["Alice", "Bob", "Charlie", "David"]
        
        report = analyzer.analyze(speaking_times, participants, interruptions_count=2)
        
        self.assertEqual(report["dominant_speaker"], "Alice")
        self.assertIn("Charlie", report["silent_participants"])
        self.assertIn("David", report["silent_participants"])
        self.assertEqual(report["interruptions"], 2)
        # Verify balance calculation lies within bound
        self.assertTrue(0.0 <= report["meeting_balance"] <= 1.0)

    def test_recommendation_engine(self) -> None:
        engine = RecommendationEngine()
        
        # Define mock state
        state = LiveMeetingState(
            meeting_id=10,
            user_id=1,
            participants=["Alice", "Bob"],
            speaking_times={"Alice": 200.0, "Bob": 0.0}, # Bob is silent
            action_items=[
                {"task": "Task 1", "owner": "Unassigned", "deadline": "Friday"},
                {"task": "Task 2", "owner": "Unassigned", "deadline": "Friday"},
                {"task": "Task 3", "owner": "Unassigned", "deadline": "Friday"}, # 3 unowned actions
            ],
            insights=[
                CopilotInsight(
                    meeting_id=10,
                    insight_type="deadline",
                    title="Deadline",
                    content="Due Friday",
                    confidence=0.8,
                    metadata={"deadline": "Friday", "task": "Unassigned Task", "owner": "Unassigned"}
                )
            ]
        )

        recs = engine.generate(state, meeting_duration_minutes=5.0)
        
        contents = [r.content for r in recs]
        self.assertTrue(any("Alice has not spoken" in c or "Bob has not spoken" in c for c in contents))
        self.assertTrue(any("action items have no owner" in c for c in contents))
        self.assertTrue(any("Deadline 'Friday' mentioned without assignee" in c for c in contents))

    def test_copilot_service_and_event_flow(self) -> None:
        # Mock WebSocket broadcast
        mock_ws_manager = get_copilot_socket_manager()
        mock_ws_manager.dispatch_copilot_update = MagicMock()
        
        bus = EventBus()
        
        # Start meeting
        self.service.handle_meeting_started(meeting_id=20, user_id=1)
        
        # Publish transcript event
        event = TranscriptSavedEvent(
            user_id=1,
            meeting_id=20,
            payload={
                "text": "We decided to postpone the migration until next week because of authentication blockers.",
                "speaker_name": "Alice",
                "start_seconds": 10.0,
                "end_seconds": 15.0,
            }
        )
        
        bus.publish(event)
        
        # Assert metrics update
        self.assertEqual(self.service.metrics["processing_count"], 1)
        self.assertTrue(self.service.metrics["insights_generated"] > 0)
        
        # Assert state holds correct insights
        state = self.service.get_meeting_state(20)
        self.assertIsNotNone(state)
        insight_types = [ins.insight_type for ins in state.insights]
        self.assertIn("decision", insight_types)
        self.assertIn("risk", insight_types)
        
        # Verify timeline sorting and socket broadcast
        self.assertTrue(mock_ws_manager.dispatch_copilot_update.called)
        broadcast_args = mock_ws_manager.dispatch_copilot_update.call_args[1]
        self.assertEqual(broadcast_args["meeting_id"], 20)
        self.assertIn("timeline", broadcast_args["update_data"])
        self.assertIn("engagement", broadcast_args["update_data"])
        
        # Timeline items should be sorted
        timeline = broadcast_args["update_data"]["timeline"]
        self.assertTrue(len(timeline) >= 2)

    def test_planner_live_insight_context_injection(self) -> None:
        # Start meeting state and seed decision insight
        self.service.handle_meeting_started(meeting_id=30, user_id=1)
        state = self.service.get_meeting_state(30)
        state.insights.append(CopilotInsight(
            meeting_id=30,
            insight_type="decision",
            title="API specifications approved",
            content="We decided to approve the API specs.",
            confidence=0.9,
            speaker="Alice"
        ))

        # Set current meeting context
        from app.memory import current_meeting_id
        token = current_meeting_id.set(30)
        
        try:
            planner = Planner()
            planner._provider = MagicMock()
            planner._provider.generate.return_value = type("Res", (), {"content": '{"intent":"GENERAL_CHAT","confidence":0.9,"tools":[],"parameters":{},"reasoning":"general response"}'})()

            planner.plan("Review active decisions")

            # Assert generator call arguments include the copilot context key
            args = planner._provider.generate.call_args[0][0]
            self.assertIn("live_copilot_insights", args)
            self.assertIn("We decided to approve the API specs.", args)
        finally:
            current_meeting_id.reset(token)


if __name__ == "__main__":
    unittest.main()
