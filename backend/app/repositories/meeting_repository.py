"""SQLAlchemy persistence operations for meetings."""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus


class MeetingRepository:
    """Persist and retrieve Meeting entities using an injected SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with the current request's database session."""
        self._session = session

    def create_meeting(
        self,
        *,
        title: str,
        status: MeetingStatus = MeetingStatus.CREATED,
    ) -> Meeting:
        """Create, persist, and return a new meeting record."""
        meeting = Meeting(title=title, status=status)
        self._session.add(meeting)
        return self._commit_and_refresh(meeting)

    def get_meeting_by_id(self, meeting_id: int) -> Meeting | None:
        """Return a meeting by primary key, or None when it does not exist."""
        statement: Select[tuple[Meeting]] = select(Meeting).where(
            Meeting.id == meeting_id
        )
        return self._session.execute(statement).scalars().first()

    def get_running_meeting(self) -> Meeting | None:
        """Return the most recently started running meeting, if one exists."""
        statement: Select[tuple[Meeting]] = (
            select(Meeting)
            .where(Meeting.status == MeetingStatus.RUNNING)
            .order_by(Meeting.started_at.desc(), Meeting.id.desc())
        )
        return self._session.execute(statement).scalars().first()

    def update_meeting(self, meeting: Meeting) -> Meeting:
        """Persist changes already applied to a managed meeting entity."""
        return self._commit_and_refresh(meeting)

    def delete_meeting(self, meeting: Meeting) -> None:
        """Permanently delete a meeting record for future administrative workflows."""
        self._session.delete(meeting)
        self._commit()

    def list_meetings(self, *, offset: int = 0, limit: int = 100) -> Sequence[Meeting]:
        """Return meetings in newest-first order using bounded pagination."""
        if offset < 0:
            raise ValueError("offset must be zero or greater")
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")

        statement: Select[tuple[Meeting]] = (
            select(Meeting)
            .order_by(Meeting.created_at.desc(), Meeting.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return self._session.execute(statement).scalars().all()

    def _commit_and_refresh(self, meeting: Meeting) -> Meeting:
        """Commit the active transaction and reload one persisted entity."""
        self._commit()
        self._session.refresh(meeting)
        return meeting

    def _commit(self) -> None:
        """Commit changes and roll back the session if persistence fails."""
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
