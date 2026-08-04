"""SQLAlchemy persistence operations for AI-extracted action items."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem


@dataclass(frozen=True, slots=True)
class ActionItemDraft:
    """Validated AI extraction ready for persistence."""

    task: str
    owner: str | None
    due_at: datetime | None
    priority: str | None
    is_completed: bool = False


class ActionItemRepository:
    """Persist a meeting's extracted action items through an injected session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_meeting(
        self, *, meeting_id: int, items: Sequence[ActionItemDraft]
    ) -> list[ActionItem]:
        """Atomically replace previously extracted items for one meeting."""
        self._session.execute(delete(ActionItem).where(ActionItem.meeting_id == meeting_id))
        persisted = [
            ActionItem(
                meeting_id=meeting_id,
                description=item.task,
                assignee=item.owner,
                due_at=item.due_at,
                priority=item.priority,
                is_completed=item.is_completed,
            )
            for item in items
        ]
        self._session.add_all(persisted)
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
        for item in persisted:
            self._session.refresh(item)
        return persisted

    def list_for_meeting(self, meeting_id: int) -> Sequence[ActionItem]:
        """Return a meeting's action items in extraction order."""
        statement = (
            select(ActionItem)
            .where(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.id.asc())
        )
        return self._session.execute(statement).scalars().all()
