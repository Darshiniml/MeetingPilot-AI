"""Decoupled adapter that turns service notifications into typed events."""

from __future__ import annotations

from .event_bus import EventBus
from .event_models import (
    ActionItemsExtractedEvent, BaseAgentEvent, CalendarConflictEvent, EmailSentEvent,
    MeetingScheduledEvent, MeetingStartedEvent, MeetingStoppedEvent, ReminderDueEvent,
    SpeakerChangedEvent, SummaryGeneratedEvent, TranscriptSavedEvent, UserMessageEvent,
    VisionUpdatedEvent,
)
from .event_types import EventType


class EventDispatcher:
    """Publishes typed service notifications without containing business logic."""

    _EVENT_MODELS = {
        EventType.MEETING_STARTED: MeetingStartedEvent, EventType.MEETING_STOPPED: MeetingStoppedEvent,
        EventType.TRANSCRIPT_SAVED: TranscriptSavedEvent, EventType.SUMMARY_GENERATED: SummaryGeneratedEvent,
        EventType.ACTION_ITEM_CREATED: ActionItemsExtractedEvent, EventType.VISION_UPDATED: VisionUpdatedEvent,
        EventType.SPEAKER_CHANGED: SpeakerChangedEvent, EventType.CALENDAR_CONFLICT: CalendarConflictEvent,
        EventType.MEETING_SCHEDULED: MeetingScheduledEvent, EventType.EMAIL_SENT: EmailSentEvent,
        EventType.REMINDER_DUE: ReminderDueEvent, EventType.CHAT_MESSAGE: UserMessageEvent,
    }

    def __init__(self, bus: EventBus, observer=None) -> None:
        self._bus = bus
        self._subscriptions = []
        if observer is not None:
            self.register_observer(observer)

    def register_observer(self, observer) -> list[str]:
        if hasattr(observer, "attach_event_bus"):
            observer.attach_event_bus(self._bus)
        self._subscriptions.extend(self._bus.subscribe(event_type, observer.on_event) for event_type in EventType)
        return self.subscriptions

    def dispatch(self, event_type: EventType, *, user_id: int, meeting_id: int | None = None, payload: dict | None = None) -> BaseAgentEvent:
        event = self._EVENT_MODELS[event_type](user_id=user_id, meeting_id=meeting_id, payload=payload or {})
        self._bus.publish(event)
        return event

    @property
    def subscriptions(self) -> list[str]:
        return list(self._subscriptions)
