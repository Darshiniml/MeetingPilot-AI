"""Memory indexer listening to the EventBus and indexing native events."""

import logging
import uuid
import json
from typing import Any

from app.agent.events.event_models import BaseAgentEvent
from app.agent.events.event_types import EventType
from app.memory.memory_repository import MemoryRepository
from app.memory.vector_store import VectorStore
from app.memory.embedding_service import CachedEmbeddingService
from app.ai.providers import get_llm_provider

logger = logging.getLogger(__name__)


class MemoryIndexer:
    """Subscribes to events, generates vector embeddings, and stores them in DB and VectorStore."""

    def __init__(
        self,
        vector_store: VectorStore,
        repository_factory,
        embedding_service: CachedEmbeddingService,
    ) -> None:
        self._vector_store = vector_store
        self._repository_factory = repository_factory
        self._embedding_service = embedding_service

    def handle_event(self, event: BaseAgentEvent) -> None:
        """Parse incoming EventBus event and extract indexable long-term memories."""
        event_type = event.event_type
        payload = event.payload or {}
        user_id = event.user_id
        meeting_id = event.meeting_id

        title = ""
        content = ""
        memory_type = "LongTermMemory"

        if event_type == EventType.SUMMARY_GENERATED:
            memory_type = "MeetingMemory"
            title = "Meeting Summary"
            content = payload.get("summary") or payload.get("content") or ""
        elif event_type == EventType.TRANSCRIPT_SAVED:
            memory_type = "LongTermMemory"
            title = "Meeting Transcript Segment"
            # Support multiple possible payload shapes
            content = payload.get("text") or payload.get("transcript", {}).get("text") or ""
        elif event_type == EventType.ACTION_ITEM_CREATED:
            memory_type = "LongTermMemory"
            title = "Meeting Action Item"
            content = payload.get("task") or payload.get("action_item", {}).get("task") or ""
        elif event_type == EventType.CHAT_MESSAGE:
            memory_type = "ConversationMemory"
            title = "Conversation Message"
            # Support scheduler route request or direct chat
            content = payload.get("message") or payload.get("agent_message", {}).get("payload", {}).get("request") or ""
        elif event_type == EventType.MEETING_SCHEDULED:
            memory_type = "KnowledgeMemory"
            title = "Meeting Scheduled"
            content = str(payload.get("details") or payload.get("scheduling_plan") or "")
        elif event_type == EventType.EMAIL_SENT:
            memory_type = "ExecutionMemory"
            title = "Email Sent"
            content = payload.get("body") or payload.get("draft") or ""
        elif event_type == EventType.VISION_UPDATED:
            memory_type = "KnowledgeMemory"
            title = "Vision Observation"
            content = payload.get("description") or payload.get("observation") or ""
        
        # If we have indexable content, index it!
        if content and content.strip():
            self.index_memory(
                user_id=user_id,
                meeting_id=meeting_id,
                conversation_id=getattr(event, "conversation_id", None) or f"event-user:{user_id}",
                memory_type=memory_type,
                title=title,
                content=content.strip(),
                metadata={"event_id": event.event_id, "event_type": event_type.value}
            )

    def index_memory(
        self,
        user_id: int,
        memory_type: str,
        title: str,
        content: str,
        meeting_id: int | None = None,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Helper to compute embedding, score importance, write to SQLite repository, and index in VectorStore."""
        memory_id = str(uuid.uuid4())
        
        # 1. Generate Embedding
        try:
            embeddings = self._embedding_service.embed_texts([content])
            embedding = embeddings[0] if embeddings else [0.0] * 1536  # Default fallback dim
        except Exception as e:
            logger.error("Failed to generate embedding for memory indexing: %s", e)
            embedding = [0.0] * 1536

        # 2. Score Importance (use LLM or quick heuristics)
        importance_score = self.score_importance(content, memory_type)

        # 3. Persist to DB Repository
        with self._repository_factory() as session:
            repo = MemoryRepository(session)
            repo.create_memory(
                memory_id=memory_id,
                memory_type=memory_type,
                user_id=user_id,
                meeting_id=meeting_id,
                conversation_id=conversation_id,
                title=title,
                content=content,
                embedding=embedding,
                metadata=metadata,
                importance_score=importance_score,
            )

        # 4. Write to VectorStore
        self._vector_store.add(
            memory_id=memory_id,
            embedding=embedding,
            user_id=user_id,
            memory_type=memory_type
        )
        
        logger.info("Indexed memory: id=%s type=%s importance=%.2f", memory_id, memory_type, importance_score)
        return memory_id

    def score_importance(self, content: str, memory_type: str) -> float:
        """Rate the long-term semantic value of the content."""
        # Baseline heuristics
        heuristics = {
            "MeetingMemory": 0.8,
            "PreferenceMemory": 0.9,
            "KnowledgeMemory": 0.7,
            "ReflectionMemory": 0.7,
            "ConversationMemory": 0.5,
            "ExecutionMemory": 0.5,
            "LongTermMemory": 0.6,
        }
        score = heuristics.get(memory_type, 0.5)

        # Try to refine with LLM rating if provider is running
        try:
            provider = get_llm_provider()
            prompt = (
                "On a scale of 0.0 to 1.0, rate the long-term importance of the following content for a personal assistant memory system "
                "(0.0 = temporary noise/junk, 1.0 = critical user preference, key scheduler request or project summary).\n"
                f"Content: {content}\n"
                "Return ONLY a float value between 0.0 and 1.0. Do not include any explanation."
            )
            res = provider.generate(prompt)
            score_str = res.content.strip()
            # Clean non-numeric characters from response
            import re
            cleaned = re.findall(r"[-+]?\d*\.\d+|\d+", score_str)
            if cleaned:
                parsed = float(cleaned[0])
                if 0.0 <= parsed <= 1.0:
                    score = parsed
        except Exception:
            pass # Fall back to heuristics if model is offline or takes too long

        return score
