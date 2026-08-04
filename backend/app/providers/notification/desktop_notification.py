from __future__ import annotations

import logging
from typing import Any
from app.providers.notification.local_notification import LocalNotificationProvider

logger = logging.getLogger(__name__)

class DesktopNotificationProvider(LocalNotificationProvider):
    """Stub notifier simulating system level desktop OS alert popups."""
    
    def send_notification(
        self,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "INFO",
        workflow_id: str | None = None,
        meeting_id: int | None = None
    ) -> bool:
        # Save to SQLite database
        super().send_notification(title, message, category, severity, workflow_id, meeting_id)
        
        logger.info("[OS System Alert] [%s] [%s] Title: %s | Message: %s", severity, category, title, message)
        return True

    def get_health(self) -> dict[str, Any]:
        h = super().get_health()
        h["capabilities"].append("desktop_popups")
        return h
