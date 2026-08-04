"""Named event handlers that defer eligibility to the autonomous policy."""

from __future__ import annotations

from .agent_observer import AgentObserver
from .event_models import CalendarConflictEvent, EmailSentEvent, MeetingStoppedEvent, SummaryGeneratedEvent, TranscriptSavedEvent


def handle_transcript_saved(observer: AgentObserver, event: TranscriptSavedEvent): return observer.on_event(event)
def handle_meeting_stopped(observer: AgentObserver, event: MeetingStoppedEvent): return observer.on_event(event)
def handle_summary_generated(observer: AgentObserver, event: SummaryGeneratedEvent): return observer.on_event(event)
def handle_calendar_conflict(observer: AgentObserver, event: CalendarConflictEvent): return observer.on_event(event)
def handle_email_sent(observer: AgentObserver, event: EmailSentEvent): return observer.on_event(event)
