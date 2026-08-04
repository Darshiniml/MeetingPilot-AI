"""Read-only HTTP endpoints for meeting history."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_meeting_history_service
from app.schemas.meeting_history_schema import (
    ActionItemDetailResponse,
    MeetingDetailResponse,
    MeetingHistoryItemResponse,
    MeetingHistoryPageResponse,
    TranscriptDetailResponse,
)
from app.schemas.meeting_schema import SummaryResponse
from app.services.meeting_history_service import MeetingHistoryService


router = APIRouter(prefix="/meetings", tags=["meeting-history"])
MeetingHistoryServiceDependency = Annotated[
    MeetingHistoryService, Depends(get_meeting_history_service)
]


@router.get("", response_model=MeetingHistoryPageResponse)
def list_meetings(
    service: MeetingHistoryServiceDependency,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> MeetingHistoryPageResponse:
    """Return a newest-first, paginated meeting history."""
    meetings, total = service.list_meetings(offset=offset, limit=limit)
    return MeetingHistoryPageResponse(
        items=[
            MeetingHistoryItemResponse(
                id=item.id,
                title=item.title,
                start_time=item.start_time,
                end_time=item.end_time,
                duration=item.duration,
                transcript_count=item.transcript_count,
                summary_available=item.summary_available,
                participants=item.participants,
                action_items=item.action_items,
                meeting_status=item.meeting_status.value,
                created_at=item.created_at,
            )
            for item in meetings
        ],
        offset=offset,
        limit=limit,
        total=total,
    )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
def get_meeting(
    meeting_id: int, service: MeetingHistoryServiceDependency
) -> MeetingDetailResponse:
    """Return one meeting's full transcript, summary, and action items."""
    meeting = service.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status.value,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        duration=meeting.duration,
        transcript=[
            TranscriptDetailResponse(
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                language=chunk.language,
                confidence=chunk.confidence,
            )
            for chunk in meeting.transcript
        ],
        summary=meeting.summary,
        action_items=[
            ActionItemDetailResponse(
                id=item.id,
                task=item.task,
                owner=item.owner,
                due_date=item.due_date,
                priority=item.priority,
                status=item.status,
            )
            for item in meeting.action_items
        ],
    )


@router.get("/{meeting_id}/transcript", response_model=list[TranscriptDetailResponse])
def get_meeting_transcript(
    meeting_id: int, service: MeetingHistoryServiceDependency
) -> list[TranscriptDetailResponse]:
    """Return one meeting's transcript ordered by its chunk timestamp."""
    transcript = service.get_transcript(meeting_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return [
        TranscriptDetailResponse(
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            start_seconds=chunk.start_seconds,
            end_seconds=chunk.end_seconds,
            language=chunk.language,
            confidence=chunk.confidence,
        )
        for chunk in transcript
    ]


@router.get("/{meeting_id}/summary", response_model=SummaryResponse)
def get_meeting_history_summary(
    meeting_id: int, service: MeetingHistoryServiceDependency
) -> SummaryResponse:
    """Return one previously generated meeting summary."""
    summary = service.get_summary(meeting_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary has not been generated")
    return SummaryResponse(meeting_id=meeting_id, content=summary)


@router.get("/{meeting_id}/actions", response_model=list[ActionItemDetailResponse])
def get_meeting_actions(
    meeting_id: int, service: MeetingHistoryServiceDependency
) -> list[ActionItemDetailResponse]:
    """Return all action items extracted for one meeting."""
    action_items = service.get_action_items(meeting_id)
    if action_items is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return [
        ActionItemDetailResponse(
            id=item.id,
            task=item.task,
            owner=item.owner,
            due_date=item.due_date,
            priority=item.priority,
            status=item.status,
        )
        for item in action_items
    ]
