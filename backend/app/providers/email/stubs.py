from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class GmailProviderWrapper:
    """Wrapper that dynamically loads production Gmail integration at runtime."""
    
    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id
        self._provider = None

    def _get_provider(self) -> Any:
        if self._provider is None:
            from app.integrations.gmail.gmail_provider import GmailProvider
            self._provider = GmailProvider(self.session, self.user_id)
        return self._provider

    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        try:
            provider = self._get_provider()
            if hasattr(provider, "send_email"):
                provider.send_email(recipient, subject, html_content)
            elif hasattr(provider, "create_draft"):
                provider.create_draft(recipient, subject, html_content)
            return True
        except Exception as e:
            logger.error("Gmail Provider error: %s", e)
            return False

    def save_draft(self, recipient: str, subject: str, html_content: str) -> dict[str, Any]:
        try:
            provider = self._get_provider()
            if hasattr(provider, "create_draft"):
                draft = provider.create_draft(recipient, subject, html_content)
                return {"draft_id": draft.get("id"), "status": "DRAFT", "recipient": recipient, "subject": subject}
        except Exception:
            pass
        from app.providers.email.local_email import LocalEmailProvider
        return LocalEmailProvider().save_draft(recipient, subject, html_content)

    def list_drafts(self) -> list[dict[str, Any]]:
        return []

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        return {}

    def get_health(self) -> dict[str, Any]:
        status = "healthy"
        err = None
        try:
            provider = self._get_provider()
        except Exception as e:
            status = "degraded"
            err = str(e)
            
        return {
            "status": status,
            "latency_ms": 110,
            "version": "1.0.0",
            "capabilities": ["gmail_sending", "online_sync"],
            "last_sync": None,
            "error_info": err
        }

class MailtrapProvider:
    """Stub email provider for Mailtrap sandbox environment integrations."""
    
    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        logger.info("[Mailtrap Sandbox] Message dispatched: recipient=%s subject=%s", recipient, subject)
        return True

    def save_draft(self, recipient: str, subject: str, html_content: str) -> dict[str, Any]:
        return {"draft_id": "mailtrap-draft-123", "status": "DRAFT"}

    def list_drafts(self) -> list[dict[str, Any]]:
        return []

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        return {}

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 5,
            "version": "1.0.0",
            "capabilities": ["sandbox_email"],
            "last_sync": None,
            "error_info": None
        }

class SendGridProvider:
    """Stub email provider representing SendGrid web API integration."""
    
    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        logger.info("[SendGrid API] Message sent: %s", subject)
        return True

    def save_draft(self, recipient: str, subject: str, html_content: str) -> dict[str, Any]:
        return {"draft_id": "sg-draft-123", "status": "DRAFT"}

    def list_drafts(self) -> list[dict[str, Any]]:
        return []

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        return {}

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 8,
            "version": "1.0.0",
            "capabilities": ["sendgrid_api"],
            "last_sync": None,
            "error_info": None
        }

class ResendProvider:
    """Stub email provider representing Resend direct mailing integration."""
    
    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        logger.info("[Resend API] Message sent: %s", subject)
        return True

    def save_draft(self, recipient: str, subject: str, html_content: str) -> dict[str, Any]:
        return {"draft_id": "resend-draft-123", "status": "DRAFT"}

    def list_drafts(self) -> list[dict[str, Any]]:
        return []

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        return {}

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 6,
            "version": "1.0.0",
            "capabilities": ["resend_api"],
            "last_sync": None,
            "error_info": None
        }
