"""Calendar provider abstraction and mock implementation."""

from typing import Protocol
from app.scheduler.schemas import MeetingDetails, CalendarPreview

class CalendarProvider(Protocol):
    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        ...

    def create_event(self, details: MeetingDetails) -> dict:
        ...

    def update_event(self, event_id: str, details: MeetingDetails) -> dict:
        ...

    def delete_event(self, event_id: str) -> None:
        ...

    def list_events(self) -> list[dict]:
        ...

class MockCalendarProvider:
    """In-memory mock calendar for the initial phase."""
    
    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        # Mock logic: always available, no conflicts.
        return CalendarPreview(
            provider="mock",
            available=True,
            conflicts=[],
            suggestions=[]
        )

    def create_event(self, details: MeetingDetails) -> dict:
        from datetime import datetime, timezone
        return {
            "event_id": f"mock_event_id_{details.title.replace(' ', '_')}",
            "calendar_link": f"http://mock-link/{details.title.replace(' ', '_')}",
            "meeting_start": datetime.now(timezone.utc),
            "meeting_end": datetime.now(timezone.utc),
            "google_meet_link": "https://meet.google.com/mock-link"
        }

    def update_event(self, event_id: str, details: MeetingDetails) -> dict:
        from datetime import datetime, timezone
        return {
            "event_id": event_id,
            "calendar_link": f"http://mock-link/{details.title.replace(' ', '_')}",
            "meeting_start": datetime.now(timezone.utc),
            "meeting_end": datetime.now(timezone.utc)
        }

    def delete_event(self, event_id: str) -> None:
        pass

    def list_events(self) -> list[dict]:
        return []
