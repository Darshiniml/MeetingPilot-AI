"""Orchestrator combining retriever, ranker, indexer, compactor, and metrics."""

import logging
import time
from typing import Any
from contextlib import asynccontextmanager

from app.database.session import SessionLocal
from app.memory.vector_store import SQLiteVectorStore
from app.memory.memory_repository import MemoryRepository
from app.memory.embedding_service import CachedEmbeddingService
from app.memory.memory_retriever import MemoryRetriever
from app.memory.memory_ranker import MemoryRanker
from app.memory.memory_compactor import MemoryCompactor
from app.memory.memory_indexer import MemoryIndexer

logger = logging.getLogger(__name__)


class MemoryManager:
    """Entry point coordinating the persistent long-term semantic memory sub-modules."""

    def __init__(self, use_mock_store: bool = False, session_factory: Any = None) -> None:
        self.embedding_service = CachedEmbeddingService()
        self.session_factory = session_factory or SessionLocal
        
        # Configure VectorStore
        if use_mock_store:
            from app.memory.vector_store import MockVectorStore
            self.vector_store = MockVectorStore()
        else:
            self.vector_store = SQLiteVectorStore(self.session_factory)
        
        self.retriever = MemoryRetriever(self.vector_store, self.session_factory)
        self.ranker = MemoryRanker()
        self.compactor = MemoryCompactor(self.session_factory)
        self.indexer = MemoryIndexer(self.vector_store, self.session_factory, self.embedding_service)

        # Metrics counters
        self.metrics = {
            "embedding_generation_time_ms": 0.0,
            "memory_hits": 0,
            "memory_misses": 0,
            "retrieval_latency_ms": 0.0,
            "indexing_latency_ms": 0.0,
            "compaction_savings": 0,
        }

    def retrieve_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
        memory_type: str | None = None,
        current_meeting_id: int | None = None,
        current_conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic vector search, rank matches, and return consolidated memories."""
        start_time = time.perf_counter()
        
        # 1. Generate query embedding
        emb_start = time.perf_counter()
        query_embeddings = self.embedding_service.embed_texts([query])
        query_embedding = query_embeddings[0] if query_embeddings else [0.0] * 1536
        self.metrics["embedding_generation_time_ms"] += (time.perf_counter() - emb_start) * 1000

        # 2. Retrieve vector store matches
        matches = self.retriever.retrieve(
            query_embedding=query_embedding,
            limit=limit,
            user_id=user_id,
            memory_type=memory_type
        )

        # Update hit/miss metrics
        if matches:
            self.metrics["memory_hits"] += 1
        else:
            self.metrics["memory_misses"] += 1

        # 3. Composite Rank matches
        ranked_results = self.ranker.rank(
            memories=matches,
            current_meeting_id=current_meeting_id,
            current_user_id=user_id,
            current_conversation_id=current_conversation_id
        )

        latency = (time.perf_counter() - start_time) * 1000
        self.metrics["retrieval_latency_ms"] += latency
        logger.info("MemoryManager retrieved %d ranked memories in %.2f ms", len(ranked_results), latency)
        
        return ranked_results

    def compact_memories(self, user_id: int) -> int:
        """Scan and merge duplicate or redundant memory records."""
        start_time = time.perf_counter()
        savings = self.compactor.compact(user_id)
        self.metrics["compaction_savings"] += savings
        logger.info("MemoryManager compaction complete: saved %d rows in %.2f ms", savings, (time.perf_counter() - start_time) * 1000)
        return savings

    def add_custom_memory(
        self,
        user_id: int,
        memory_type: str,
        title: str,
        content: str,
        meeting_id: int | None = None,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Directly index a customized memory string."""
        start_time = time.perf_counter()
        memory_id = self.indexer.index_memory(
            user_id=user_id,
            memory_type=memory_type,
            title=title,
            content=content,
            meeting_id=meeting_id,
            conversation_id=conversation_id,
            metadata=metadata
        )
        self.metrics["indexing_latency_ms"] += (time.perf_counter() - start_time) * 1000
        return memory_id

    def get_metrics(self) -> dict[str, Any]:
        """Fetch real-time metrics, including memory count from the SQLite database."""
        # Query total memory count from database
        total_count = 0
        try:
            with self.session_factory() as session:
                from app.memory.memory_models import Memory
                from sqlalchemy import func
                total_count = session.query(func.count(Memory.memory_id)).scalar() or 0
        except Exception:
            pass

        return {
            **self.metrics,
            "memory_count": total_count,
            "average_embedding_latency_ms": self.embedding_service.get_average_latency_ms()
        }


# Global singleton instance
_memory_manager = None


def get_memory_manager(use_mock_store: bool = False) -> MemoryManager:
    """Singleton getter for the shared MemoryManager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(use_mock_store=use_mock_store)
    return _memory_manager
