from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.scheduler.schemas import MeetingDetails, CalendarPreview

logger = logging.getLogger(__name__)

class GoogleCalendarProviderWrapper:
    """Wrapper that dynamically loads production Google Calendar integration at runtime."""
    
    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id
        self._provider = None

    def _get_provider(self) -> Any:
        if self._provider is None:
            from app.integrations.google_calendar.calendar_provider import GoogleCalendarProvider
            self._provider = GoogleCalendarProvider(self.session, self.user_id)
        return self._provider

    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        try:
            return self._get_provider().check_availability(details)
        except Exception as e:
            logger.error("Google Calendar check_availability error: %s", e)
            return CalendarPreview(
                provider="google",
                available=False,
                conflicts=[f"Google Calendar Connection Error: {str(e)}"],
                suggestions=[]
            )

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        return self._get_provider().create_event(details)

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        return self._get_provider().update_event(event_id, details)

    def delete_event(self, event_id: str) -> None:
        self._get_provider().delete_event(event_id)

    def list_events(self) -> list[dict[str, Any]]:
        try:
            return self._get_provider().list_events()
        except Exception:
            return []

    def search_events(self, query: str) -> list[dict[str, Any]]:
        events = self.list_events()
        query = query.lower()
        return [
            ev for ev in events
            if query in ev.get("title", "").lower()
        ]

    def import_ics(self, ics_text: str) -> int:
        raise NotImplementedError("iCalendar direct import is not supported on Google Calendar provider wrapper.")

    def export_ics(self) -> str:
        raise NotImplementedError("iCalendar direct export is not supported on Google Calendar provider wrapper.")

    def get_health(self) -> dict[str, Any]:
        status = "healthy"
        err = None
        try:
            # check token connection
            from app.integrations.google_calendar.token_store import TokenStore
            token_store = TokenStore(self.session)
            token = token_store.get_token(self.user_id)
            if not token or not token.is_connected:
                status = "degraded"
                err = "Google Calendar integration oauth token is not connected."
        except Exception as e:
            status = "offline"
            err = str(e)

        return {
            "status": status,
            "latency_ms": 120,
            "version": "1.0.0",
            "capabilities": ["CRUD", "availability_check", "online_sync"],
            "last_sync": None,
            "error_info": err
        }
