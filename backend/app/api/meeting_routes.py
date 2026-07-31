"""HTTP endpoints for the meeting lifecycle."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.dependencies import get_meeting_service
from app.schemas.meeting_schema import MeetingActionResponse, MeetingStatusResponse, SummaryResponse
from app.services.meeting_service import MeetingService


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
def stop_meeting(response: Response, service: MeetingServiceDependency) -> MeetingActionResponse:
    """Stop the current meeting session."""
    state = service.stop_meeting()
    if state.meeting_id is not None:
        response.headers["X-Meeting-Id"] = str(state.meeting_id)
    return MeetingActionResponse(message="Meeting Stopped", running=state.running)


@router.get("/{meeting_id}/summary", response_model=SummaryResponse)
def get_meeting_summary(meeting_id: int, service: MeetingServiceDependency) -> SummaryResponse:
    """Return the generated summary for one completed meeting."""
    summary = service.get_summary(meeting_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary has not been generated")
    return SummaryResponse(meeting_id=meeting_id, content=summary.content)
