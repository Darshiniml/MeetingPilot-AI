from __future__ import annotations

from typing import Protocol, Any

class NotificationProvider(Protocol):
    """Protocol interface defining requirements for Notification service plugins."""
    
    def send_notification(
        self,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "INFO",
        workflow_id: str | None = None,
        meeting_id: int | None = None
    ) -> bool:
        """Transmit or record a notification event."""
        ...

    def list_notifications(
        self,
        is_read: bool | None = None,
        category: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve recent registered notifications logs list."""
        ...

    def mark_as_read(self, notification_id: str) -> None:
        """Mark a notification alert as read."""
        ...

    def get_health(self) -> dict[str, Any]:
        """Retrieve dynamic health metrics details for this provider instance."""
        ...
