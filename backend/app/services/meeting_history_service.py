"""Business-layer mapping for read-only meeting history."""

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from app.models.meeting import Meeting, MeetingStatus
from app.repositories.meeting_history_repository import (
    MeetingHistoryPage,
    MeetingHistoryRepository,
)


@dataclass(frozen=True, slots=True)
class MeetingHistoryItem:
    id: int
    title: str
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    transcript_count: int
    summary_available: bool
    participants: int
    action_items: int
    meeting_status: MeetingStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MeetingTranscriptDetail:
    chunk_index: int
    text: str
    start_seconds: float
    end_seconds: float
    language: str
    confidence: float | None


@dataclass(frozen=True, slots=True)
class MeetingActionItemDetail:
    id: int
    task: str
    owner: str | None
    due_date: datetime | None
    priority: str | None
    status: str


@dataclass(frozen=True, slots=True)
class MeetingDetail:
    id: int
    title: str
    status: MeetingStatus
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    transcript: Sequence[MeetingTranscriptDetail]
    summary: str | None
    action_items: Sequence[MeetingActionItemDetail]


class MeetingHistoryService:
    """Expose history read models without leaking ORM concerns to the API."""

    def __init__(self, repository: MeetingHistoryRepository) -> None:
        self._repository = repository

    def list_meetings(self, *, offset: int, limit: int) -> tuple[Sequence[MeetingHistoryItem], int]:
        page: MeetingHistoryPage = self._repository.list_meetings(offset=offset, limit=limit)
        return (
            tuple(
                MeetingHistoryItem(
                    id=record.meeting.id,
                    title=record.meeting.title,
                    start_time=record.meeting.started_at,
                    end_time=record.meeting.ended_at,
                    duration=self._duration(record.meeting),
                    transcript_count=record.transcript_count,
                    summary_available=record.summary_available,
                    participants=0,
                    action_items=record.action_item_count,
                    meeting_status=record.meeting.status,
                    created_at=record.meeting.created_at,
                )
                for record in page.records
            ),
            page.total,
        )

    def get_meeting(self, meeting_id: int) -> MeetingDetail | None:
        meeting = self._repository.get_meeting_details(meeting_id)
        if meeting is None:
            return None
        return MeetingDetail(
            id=meeting.id,
            title=meeting.title,
            status=meeting.status,
            start_time=meeting.started_at,
            end_time=meeting.ended_at,
            duration=self._duration(meeting),
            transcript=tuple(
                MeetingTranscriptDetail(
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    language=chunk.language,
                    confidence=chunk.confidence,
                )
                for chunk in meeting.transcripts
            ),
            summary=meeting.summary.content if meeting.summary else None,
            action_items=tuple(
                MeetingActionItemDetail(
                    id=item.id,
                    task=item.description,
                    owner=item.assignee,
                    due_date=item.due_at,
                    priority=item.priority,
                    status="Completed" if item.is_completed else "Pending",
                )
                for item in meeting.action_items
            ),
        )

    def get_transcript(self, meeting_id: int) -> Sequence[MeetingTranscriptDetail] | None:
        """Return one meeting's transcript in chronological chunk order."""
        meeting = self.get_meeting(meeting_id)
        return None if meeting is None else meeting.transcript

    def get_summary(self, meeting_id: int) -> str | None:
        """Return generated summary content; None covers absent meetings and summaries."""
        meeting = self.get_meeting(meeting_id)
        return None if meeting is None else meeting.summary

    def get_action_items(self, meeting_id: int) -> Sequence[MeetingActionItemDetail] | None:
        """Return all extracted action items for one meeting."""
        meeting = self.get_meeting(meeting_id)
        return None if meeting is None else meeting.action_items

    @staticmethod
    def _duration(meeting: Meeting) -> float | None:
        if meeting.started_at is None or meeting.ended_at is None:
            return None
        return (meeting.ended_at - meeting.started_at).total_seconds()
