"""Named events that can be observed by the autonomous agent."""

from enum import Enum


class EventType(str, Enum):
    MEETING_STARTED = "meeting_started"
    MEETING_STOPPED = "meeting_stopped"
    TRANSCRIPT_SAVED = "transcript_saved"
    SUMMARY_GENERATED = "summary_generated"
    ACTION_ITEM_CREATED = "action_item_created"
    SPEAKER_CHANGED = "speaker_changed"
    VISION_UPDATED = "vision_updated"
    CALENDAR_CONFLICT = "calendar_conflict"
    MEETING_SCHEDULED = "meeting_scheduled"
    EMAIL_SENT = "email_sent"
    REMINDER_DUE = "reminder_due"
    CHAT_MESSAGE = "chat_message"
