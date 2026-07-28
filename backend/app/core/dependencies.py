"""Application dependency composition for HTTP request handling."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.meeting_repository import MeetingRepository
from app.services.meeting_service import MeetingService


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_meeting_service(session: DatabaseSession) -> MeetingService:
    """Build a request-scoped MeetingService with its repository dependency."""
    return MeetingService(MeetingRepository(session))
