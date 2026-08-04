"""Public response schemas for read-only meeting history."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MeetingHistoryItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    transcript_count: int
    summary_available: bool
    participants: int
    action_items: int
    meeting_status: str
    created_at: datetime


class MeetingHistoryPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MeetingHistoryItemResponse]
    offset: int
    limit: int
    total: int


class TranscriptDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_index: int
    text: str
    start_seconds: float
    end_seconds: float
    language: str
    confidence: float | None


class ActionItemDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    task: str
    owner: str | None
    due_date: datetime | None
    priority: str | None
    status: str


class MeetingDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    status: str
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    transcript: list[TranscriptDetailResponse]
    summary: str | None
    action_items: list[ActionItemDetailResponse]
