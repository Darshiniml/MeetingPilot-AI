"""Retrieves semantic memory records using vector store similarity scores."""

import logging
import time
from typing import Any

from app.memory.vector_store import VectorStore
from app.memory.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Combines vector search with metadata-driven repository fetches."""

    def __init__(self, vector_store: VectorStore, repository_factory) -> None:
        self._vector_store = vector_store
        self._repository_factory = repository_factory

    def retrieve(
        self,
        query_embedding: list[float],
        limit: int = 10,
        user_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query the vector store and return matched memory metadata structures."""
        start_time = time.perf_counter()
        matches = self._vector_store.search(
            query_embedding=query_embedding,
            limit=limit,
            user_id=user_id,
            memory_type=memory_type
        )
        
        latency = time.perf_counter() - start_time
        logger.info("Vector search retrieved %d candidates in %.2f ms", len(matches), latency * 1000)

        if not matches:
            return []

        # Connect DB to increment access stats
        with self._repository_factory() as session:
            repo = MemoryRepository(session)
            for match in matches:
                try:
                    repo.increment_access(match["memory_id"])
                except Exception as e:
                    logger.warning("Could not increment access counter for %s: %s", match["memory_id"], e)

        return matches
