from __future__ import annotations

from typing import Protocol, Any

class EmailProvider(Protocol):
    """Protocol interface defining requirements for Email provider plugins."""
    
    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        """Send a draft email to target recipients."""
        ...

    def save_draft(self, recipient: str, subject: str, html_content: str) -> dict[str, Any]:
        """Save a new draft email configuration inside outbox / local storage."""
        ...

    def list_drafts(self) -> list[dict[str, Any]]:
        """Retrieve list of drafts in local mailbox / outbox storage."""
        ...

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        """Retrieve full details of a specific draft email."""
        ...

    def get_health(self) -> dict[str, Any]:
        """Retrieve dynamic health metrics details for this provider instance."""
        ...
