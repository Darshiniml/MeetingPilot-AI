"""SQLAlchemy persistence operations for meeting summaries."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.summary import Summary


class SummaryRepository:
    """Persist and retrieve the single generated summary for a meeting."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_meeting(self, meeting_id: int) -> Summary | None:
        statement = select(Summary).where(Summary.meeting_id == meeting_id)
        return self._session.execute(statement).scalars().first()

    def upsert_for_meeting(self, *, meeting_id: int, content: str) -> Summary:
        summary = self.get_for_meeting(meeting_id)
        if summary is None:
            summary = Summary(meeting_id=meeting_id, content=content)
            self._session.add(summary)
        else:
            summary.content = content
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
        self._session.refresh(summary)
        return summary
