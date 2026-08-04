"""Repository pattern managing CRUD persistency for memories in SQLite."""

import json
from datetime import datetime, timezone
from typing import Any, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from app.memory.memory_models import Memory, utc_now


class MemoryRepository:
    """Handles persistence and updates of memory ORM objects."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_memory(
        self,
        *,
        memory_id: str,
        memory_type: str,
        user_id: int,
        title: str,
        content: str,
        embedding: list[float],
        meeting_id: int | None = None,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 0.0,
    ) -> Memory:
        """Create and commit a new Memory entry in SQLite."""
        memory = Memory(
            memory_id=memory_id,
            memory_type=memory_type,
            user_id=user_id,
            meeting_id=meeting_id,
            conversation_id=conversation_id,
            title=title,
            content=content,
            embedding=json.dumps(embedding),
            metadata_json=json.dumps(metadata or {}),
            importance_score=importance_score,
            created_at=utc_now(),
            updated_at=utc_now(),
            last_accessed=utc_now(),
            access_count=0,
        )
        self._session.add(memory)
        self._session.commit()
        self._session.refresh(memory)
        return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        """Fetch a single Memory by ID."""
        statement = select(Memory).where(Memory.memory_id == memory_id)
        return self._session.execute(statement).scalar_one_or_none()

    def update_memory(
        self,
        memory_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> Memory | None:
        """Update fields of an existing Memory."""
        memory = self.get_memory(memory_id)
        if not memory:
            return None

        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if embedding is not None:
            memory.embedding = json.dumps(embedding)
        if metadata is not None:
            memory.metadata_json = json.dumps(metadata)
        if importance_score is not None:
            memory.importance_score = importance_score

        memory.updated_at = utc_now()
        self._session.commit()
        self._session.refresh(memory)
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a Memory entry."""
        memory = self.get_memory(memory_id)
        if not memory:
            return False
        self._session.delete(memory)
        self._session.commit()
        return True

    def list_memories(
        self,
        *,
        user_id: int | None = None,
        memory_type: str | None = None,
        meeting_id: int | None = None,
    ) -> Sequence[Memory]:
        """List memories matching specific filters."""
        stmt = select(Memory)
        if user_id is not None:
            stmt = stmt.where(Memory.user_id == user_id)
        if memory_type is not None:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if meeting_id is not None:
            stmt = stmt.where(Memory.meeting_id == meeting_id)
        
        stmt = stmt.order_by(Memory.created_at.desc())
        return self._session.execute(stmt).scalars().all()

    def increment_access(self, memory_id: str) -> None:
        """Increment the access count and update the last accessed timestamp."""
        stmt = (
            update(Memory)
            .where(Memory.memory_id == memory_id)
            .values(
                access_count=Memory.access_count + 1,
                last_accessed=utc_now()
            )
        )
        self._session.execute(stmt)
        self._session.commit()
