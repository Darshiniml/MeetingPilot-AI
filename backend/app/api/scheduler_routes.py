"""HTTP endpoints for the AI Meeting Scheduler."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_scheduler_service, CurrentUser
from app.scheduler.scheduler_service import SchedulerService
from app.scheduler.schemas import SchedulerPlanRequest, SchedulerPlanResponse, MeetingDetails, SendInvitesRequest
from app.scheduler.meeting_parser import MeetingParserError

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

SchedulerServiceDependency = Annotated[SchedulerService, Depends(get_scheduler_service)]

@router.post("/plan", response_model=SchedulerPlanResponse)
def plan_meeting(
    request: SchedulerPlanRequest,
    service: SchedulerServiceDependency,
    user: CurrentUser
) -> SchedulerPlanResponse:
    """Parse natural language request and return a meeting plan with email draft."""
    try:
        return service.plan_meeting(request.request, user_id=user.id)
    except MeetingParserError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

@router.post("/create", response_model=dict)
def create_meeting(
    details: MeetingDetails,
    service: SchedulerServiceDependency,
    user: CurrentUser,
    meeting_id: int | None = Query(None, description="Optional existing meeting ID to link.")
) -> dict:
    """Create a calendar event and persist event details in the database."""
    try:
        return service.create_meeting_event(user_id=user.id, details=details, meeting_id=meeting_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

@router.post("/send-invites", response_model=dict)
def send_invites(
    request: SendInvitesRequest,
    service: SchedulerServiceDependency,
    user: CurrentUser
) -> dict:
    """Manually send meeting invitation emails using Gmail."""
    try:
        return service.send_meeting_invitations(
            user_id=user.id,
            meeting_id=request.meeting_id,
            attendees=request.attendees
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
