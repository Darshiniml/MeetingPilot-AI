"""HTTP endpoints for the meeting lifecycle."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.meeting_schema import MeetingActionResponse, MeetingStatusResponse
from app.services.meeting_service import MeetingService, get_meeting_service


router = APIRouter(prefix="/meeting", tags=["meeting"])

MeetingServiceDependency = Annotated[MeetingService, Depends(get_meeting_service)]


@router.get("/status", response_model=MeetingStatusResponse)
def meeting_status(service: MeetingServiceDependency) -> MeetingStatusResponse:
    """Return whether MeetingPilot currently has an active meeting."""
    state = service.get_status()
    return MeetingStatusResponse(running=state.running)


@router.post("/start", response_model=MeetingActionResponse)
def start_meeting(service: MeetingServiceDependency) -> MeetingActionResponse:
    """Start the current meeting session."""
    state = service.start_meeting()
    return MeetingActionResponse(message="Meeting Started", running=state.running)


@router.post("/stop", response_model=MeetingActionResponse)
def stop_meeting(service: MeetingServiceDependency) -> MeetingActionResponse:
    """Stop the current meeting session."""
    state = service.stop_meeting()
    return MeetingActionResponse(message="Meeting Stopped", running=state.running)
