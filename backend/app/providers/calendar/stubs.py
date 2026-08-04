from __future__ import annotations

from typing import Any
from app.scheduler.schemas import MeetingDetails, CalendarPreview

class OutlookCalendarProvider:
    """Stub calendar provider representing future Microsoft Graph integrations."""
    
    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        return CalendarPreview(
            provider="outlook",
            available=True,
            conflicts=[],
            suggestions=[]
        )

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        return {
            "event_id": f"outlook_mock_event_{details.title.replace(' ', '_')}",
            "calendar_link": "https://outlook.live.com/calendar",
            "google_meet_link": "https://teams.microsoft.com/mock-meet"
        }

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        return {"event_id": event_id}

    def delete_event(self, event_id: str) -> None:
        pass

    def list_events(self) -> list[dict[str, Any]]:
        return []

    def search_events(self, query: str) -> list[dict[str, Any]]:
        return []

    def import_ics(self, ics_text: str) -> int:
        return 0

    def export_ics(self) -> str:
        return ""

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 10,
            "version": "1.0.0",
            "capabilities": ["CRUD"],
            "last_sync": None,
            "error_info": None
        }

class CalDAVProvider:
    """Stub calendar provider representing future CalDAV standard syncing."""
    
    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        return CalendarPreview(
            provider="caldav",
            available=True,
            conflicts=[],
            suggestions=[]
        )

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        return {
            "event_id": f"caldav_mock_event_{details.title.replace(' ', '_')}",
            "calendar_link": "http://caldav.server/events",
            "google_meet_link": "https://jitsi.org/mock-meet"
        }

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        return {"event_id": event_id}

    def delete_event(self, event_id: str) -> None:
        pass

    def list_events(self) -> list[dict[str, Any]]:
        return []

    def search_events(self, query: str) -> list[dict[str, Any]]:
        return []

    def import_ics(self, ics_text: str) -> int:
        return 0

    def export_ics(self) -> str:
        return ""

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 15,
            "version": "1.0.0",
            "capabilities": ["CRUD"],
            "last_sync": None,
            "error_info": None
        }
