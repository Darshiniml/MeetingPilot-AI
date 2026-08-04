"""Abstraction and implementations for vector similarity stores."""

import json
from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.memory.memory_models import Memory


class VectorStore(ABC):
    """Abstract Base Class defining the vector storage and retrieval capabilities."""

    @abstractmethod
    def add(self, memory_id: str, embedding: list[float], user_id: int, memory_type: str) -> None:
        """Add a single vector entry."""
        pass

    @abstractmethod
    def update(self, memory_id: str, embedding: list[float]) -> None:
        """Update a vector entry."""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> None:
        """Delete a vector entry by ID."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        user_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top-K matching records based on cosine similarity."""
        pass

    @abstractmethod
    def batch_add(self, entries: list[dict[str, Any]]) -> None:
        """Efficiently write multiple vector entries."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Purge all entries from the store."""
        pass


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute the cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SQLiteVectorStore(VectorStore):
    """In-memory computed SQLite Vector Store. Highly portable, no extra packages needed."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def add(self, memory_id: str, embedding: list[float], user_id: int, memory_type: str) -> None:
        # SQLite store leverages the main memories table; we write to it via MemoryRepository/ORM.
        pass

    def update(self, memory_id: str, embedding: list[float]) -> None:
        # DB updates happen via the Session ORM.
        pass

    def delete(self, memory_id: str) -> None:
        # DB deletes happen via the Session ORM.
        pass

    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        user_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(Memory)
            if user_id is not None:
                stmt = stmt.where(Memory.user_id == user_id)
            if memory_type is not None:
                stmt = stmt.where(Memory.memory_type == memory_type)
            
            memories = session.execute(stmt).scalars().all()
            
            results = []
            for memory in memories:
                try:
                    emb = json.loads(memory.embedding)
                    score = cosine_similarity(query_embedding, emb)
                    results.append({
                        "memory_id": memory.memory_id,
                        "score": score,
                        "memory_type": memory.memory_type,
                        "user_id": memory.user_id,
                        "meeting_id": memory.meeting_id,
                        "conversation_id": memory.conversation_id,
                        "title": memory.title,
                        "content": memory.content,
                        "importance_score": memory.importance_score,
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                        "last_accessed": memory.last_accessed,
                        "access_count": memory.access_count,
                        "metadata": json.loads(memory.metadata_json) if memory.metadata_json else {}
                    })
                except Exception:
                    continue
            
            # Sort descending by cosine similarity score
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

    def batch_add(self, entries: list[dict[str, Any]]) -> None:
        # Handled at repository session level.
        pass

    def clear(self) -> None:
        with self._session_factory() as session:
            session.query(Memory).delete()
            session.commit()


class MockVectorStore(VectorStore):
    """Pure in-memory vector store implementation for testing environments."""

    def __init__(self) -> None:
        # Stores format: memory_id -> {"embedding": list[float], "metadata": dict, "user_id": int, "memory_type": str}
        self._store: dict[str, dict[str, Any]] = {}

    def add(self, memory_id: str, embedding: list[float], user_id: int, memory_type: str) -> None:
        self._store[memory_id] = {
            "embedding": embedding,
            "user_id": user_id,
            "memory_type": memory_type,
        }

    def update(self, memory_id: str, embedding: list[float]) -> None:
        if memory_id in self._store:
            self._store[memory_id]["embedding"] = embedding

    def delete(self, memory_id: str) -> None:
        self._store.pop(memory_id, None)

    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        user_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for memory_id, data in self._store.items():
            if user_id is not None and data["user_id"] != user_id:
                continue
            if memory_type is not None and data["memory_type"] != memory_type:
                continue
            score = cosine_similarity(query_embedding, data["embedding"])
            results.append({
                "memory_id": memory_id,
                "score": score,
                "user_id": data["user_id"],
                "memory_type": data["memory_type"]
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def batch_add(self, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            self.add(
                memory_id=entry["memory_id"],
                embedding=entry["embedding"],
                user_id=entry["user_id"],
                memory_type=entry["memory_type"]
            )

    def clear(self) -> None:
        self._store.clear()
