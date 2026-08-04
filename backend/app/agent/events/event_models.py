"""Strongly typed timestamped event contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .event_types import EventType


class BaseAgentEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: int
    meeting_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    event_type: EventType


def _event_model(name: str, event_type: EventType):
    return type(name, (BaseAgentEvent,), {"__annotations__": {"event_type": EventType}, "event_type": event_type})


MeetingStartedEvent = _event_model("MeetingStartedEvent", EventType.MEETING_STARTED)
MeetingStoppedEvent = _event_model("MeetingStoppedEvent", EventType.MEETING_STOPPED)
TranscriptSavedEvent = _event_model("TranscriptSavedEvent", EventType.TRANSCRIPT_SAVED)
SummaryGeneratedEvent = _event_model("SummaryGeneratedEvent", EventType.SUMMARY_GENERATED)
ActionItemCreatedEvent = _event_model("ActionItemCreatedEvent", EventType.ACTION_ITEM_CREATED)
ActionItemsExtractedEvent = _event_model("ActionItemsExtractedEvent", EventType.ACTION_ITEM_CREATED)
SpeakerChangedEvent = _event_model("SpeakerChangedEvent", EventType.SPEAKER_CHANGED)
VisionUpdatedEvent = _event_model("VisionUpdatedEvent", EventType.VISION_UPDATED)
CalendarConflictEvent = _event_model("CalendarConflictEvent", EventType.CALENDAR_CONFLICT)
MeetingScheduledEvent = _event_model("MeetingScheduledEvent", EventType.MEETING_SCHEDULED)
EmailSentEvent = _event_model("EmailSentEvent", EventType.EMAIL_SENT)
ReminderDueEvent = _event_model("ReminderDueEvent", EventType.REMINDER_DUE)
ChatMessageEvent = _event_model("ChatMessageEvent", EventType.CHAT_MESSAGE)
UserMessageEvent = _event_model("UserMessageEvent", EventType.CHAT_MESSAGE)
