"""Read-only SQLAlchemy queries for meeting history."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.action_item import ActionItem
from app.models.meeting import Meeting
from app.models.summary import Summary
from app.models.transcript import Transcript


@dataclass(frozen=True, slots=True)
class MeetingHistoryRecord:
    """A meeting paired with list-view aggregate metadata."""

    meeting: Meeting
    transcript_count: int
    summary_available: bool
    action_item_count: int


@dataclass(frozen=True, slots=True)
class MeetingHistoryPage:
    """A bounded page of history records and the matching total."""

    records: Sequence[MeetingHistoryRecord]
    total: int


class MeetingHistoryRepository:
    """Keep all meeting-history SQLAlchemy reads in one repository."""

    def __init__(self, session: Session, user_id: int | None = None) -> None:
        self._session = session
        self._user_id = user_id

    def list_meetings(self, *, offset: int, limit: int) -> MeetingHistoryPage:
        """Return newest-first meetings with transcript and summary aggregates."""
        if offset < 0:
            raise ValueError("offset must be zero or greater")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        transcript_counts = (
            select(
                Transcript.meeting_id.label("meeting_id"),
                func.count(Transcript.id).label("transcript_count"),
            )
            .group_by(Transcript.meeting_id)
            .subquery()
        )
        action_item_counts = (
            select(
                ActionItem.meeting_id.label("meeting_id"),
                func.count(ActionItem.id).label("action_item_count"),
            )
            .group_by(ActionItem.meeting_id)
            .subquery()
        )
        statement = (
            select(
                Meeting,
                func.coalesce(transcript_counts.c.transcript_count, 0),
                Summary.id.is_not(None),
                func.coalesce(action_item_counts.c.action_item_count, 0),
            )
            .outerjoin(transcript_counts, transcript_counts.c.meeting_id == Meeting.id)
            .outerjoin(Summary, Summary.meeting_id == Meeting.id)
            .outerjoin(action_item_counts, action_item_counts.c.meeting_id == Meeting.id)
        )
        
        if self._user_id is not None:
            statement = statement.where(Meeting.user_id == self._user_id)

        statement = (
            statement
            .order_by(Meeting.started_at.desc(), Meeting.id.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self._session.execute(statement).all()
        records = [
            MeetingHistoryRecord(
                meeting=meeting,
                transcript_count=int(transcript_count),
                summary_available=bool(summary_available),
                action_item_count=int(action_item_count),
            )
            for meeting, transcript_count, summary_available, action_item_count in rows
        ]
        total_stmt = select(func.count(Meeting.id))
        if self._user_id is not None:
            total_stmt = total_stmt.where(Meeting.user_id == self._user_id)
        total = int(self._session.scalar(total_stmt) or 0)
        return MeetingHistoryPage(records=records, total=total)

    def get_meeting_details(self, meeting_id: int) -> Meeting | None:
        """Return a meeting and its history relationships, or None when absent."""
        statement = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
        )
        if self._user_id is not None:
            statement = statement.where(Meeting.user_id == self._user_id)

        statement = statement.options(
            selectinload(Meeting.transcripts),
            selectinload(Meeting.summary),
            selectinload(Meeting.action_items),
        )
        return self._session.execute(statement).scalars().first()
