from __future__ import annotations

from typing import Protocol, Any
from app.scheduler.schemas import MeetingDetails, CalendarPreview

class CalendarProvider(Protocol):
    """Protocol interface defining requirements for Calendar service plugins."""
    
    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        """Verify availability window for the meeting parameters."""
        ...

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        """Create a new calendar meeting entry."""
        ...

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        """Update an existing calendar event details."""
        ...

    def delete_event(self, event_id: str) -> None:
        """Remove a calendar event from the provider database."""
        ...

    def list_events(self) -> list[dict[str, Any]]:
        """Retrieve list of all active calendar events."""
        ...

    def search_events(self, query: str) -> list[dict[str, Any]]:
        """Search calendar entries by title or metadata matching query."""
        ...

    def import_ics(self, ics_text: str) -> int:
        """Parse RFC 5545 iCalendar content and load into the database."""
        ...

    def export_ics(self) -> str:
        """Generate full RFC 5545 iCalendar string representation of calendar events."""
        ...

    def get_health(self) -> dict[str, Any]:
        """Retrieve dynamic health metrics details for this provider instance."""
        ...
