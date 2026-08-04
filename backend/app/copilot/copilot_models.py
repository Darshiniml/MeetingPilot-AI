"""Pydantic schemas and models for live copilot intelligence."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field


class CopilotInsight(BaseModel):
    """A single real-time insight detected during a live meeting."""

    insight_id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: int
    insight_type: str  # 'decision', 'risk', 'deadline', 'commitment', 'question', 'recommendation'
    title: str
    content: str
    confidence: float
    speaker: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveMeetingState(BaseModel):
    """Aggregated real-time metrics and state for an active meeting."""

    meeting_id: int
    user_id: int
    transcript_chunks: list[dict[str, Any]] = Field(default_factory=list)
    speaker_events: list[dict[str, Any]] = Field(default_factory=list)
    active_speaker: str | None = None
    participants: list[str] = Field(default_factory=list)
    insights: list[CopilotInsight] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    resolved_questions: list[str] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)
    speaking_times: dict[str, float] = Field(default_factory=dict)  # speaker -> total duration in seconds
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
