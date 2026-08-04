from __future__ import annotations

import os
import logging
from typing import Any
from app.scheduler.schemas import MeetingDetails, CalendarPreview
from app.providers.calendar.local_calendar import LocalCalendarProvider

logger = logging.getLogger(__name__)

class ICSCalendarProvider(LocalCalendarProvider):
    """File-backed calendar synchronizing events directly to an active .ics file."""
    
    def __init__(self, ics_filepath: str = "local_calendar.ics") -> None:
        self.ics_filepath = ics_filepath
        super().__init__()
        self._sync_from_ics()

    def _sync_from_ics(self) -> None:
        """Load external .ics file contents into database."""
        if not os.path.exists(self.ics_filepath):
            self._sync_to_ics()
            return

        try:
            with open(self.ics_filepath, "r", encoding="utf-8") as f:
                ics_text = f.read()
            self.import_ics(ics_text)
        except Exception as e:
            logger.error("Failed to sync from ICS file: %s", e)

    def _sync_to_ics(self) -> None:
        """Write all active database events into target .ics file."""
        try:
            ics_text = self.export_ics()
            with open(self.ics_filepath, "w", encoding="utf-8") as f:
                f.write(ics_text)
        except Exception as e:
            logger.error("Failed to sync to ICS file: %s", e)

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        res = super().create_event(details)
        self._sync_to_ics()
        return res

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        res = super().update_event(event_id, details)
        self._sync_to_ics()
        return res

    def delete_event(self, event_id: str) -> None:
        super().delete_event(event_id)
        self._sync_to_ics()

    def get_health(self) -> dict[str, Any]:
        h = super().get_health()
        h["capabilities"].append("ics_file_sync")
        return h
