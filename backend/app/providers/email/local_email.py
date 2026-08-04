from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.provider_models import LocalEmail

logger = logging.getLogger(__name__)

TEMPLATES = {
    "meeting_invitation": "<html><body><h2>Invitation: {{ title }}</h2><p>You have been invited to a meeting scheduled on {{ date }} at {{ time }}.</p></body></html>",
    "meeting_summary": "<html><body><h2>Summary: {{ title }}</h2><p>Here is the meeting summary details: {{ summary_text }}</p></body></html>",
    "action_items": "<html><body><h2>Action Items: {{ title }}</h2><p>Here are your action items: {{ items_text }}</p></body></html>"
}

class LocalEmailProvider:
    """SQLite-backed offline mailbox handling drafts, queued outbox, sent mail, and templates."""
    
    def __init__(self, db_session: Session | None = None) -> None:
        self._db = db_session
        self.version = "1.0.0"
        self.last_sync = datetime.now(timezone.utc).isoformat()
        self.error_info = None

    def _get_db(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _close_db(self, session: Session) -> None:
        if self._db is None:
            session.close()

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 3,
            "version": self.version,
            "capabilities": ["drafts", "outbox_queuing", "sent_history", "templates"],
            "last_sync": self.last_sync,
            "error_info": self.error_info
        }

    def save_draft(self, recipient: str, subject: str, html_content: str, template_name: str | None = None) -> dict[str, Any]:
        """Save a new draft email entry inside the SQLite mailbox."""
        email_id = f"email-{uuid.uuid4()}"
        email_row = LocalEmail(
            email_id=email_id,
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            status="DRAFT",
            template_name=template_name,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        session = self._get_db()
        try:
            session.add(email_row)
            session.commit()
            logger.info("Local draft saved in SQLite: %s (%s)", subject, email_id)
            return self._row_to_dict(email_row)
        finally:
            self._close_db(session)

    def send_draft(self, recipient: str, subject: str, html_content: str, attachments: list[dict[str, Any]] | None = None) -> bool:
        """Transmit message immediately via SMTP if active, otherwise queue inside Outbox."""
        from app.providers import ProviderManager
        db = self._get_db()
        config = ProviderManager.load_config(db)
        
        success = False
        if config.get("email") == "smtp":
            try:
                from app.providers.email.smtp_email import SMTPProvider
                smtp = SMTPProvider()
                success = smtp.send_draft(recipient, subject, html_content, attachments)
            except Exception as e:
                logger.error("SMTP transmission error, queuing inside local Outbox: %s", e)
                self.error_info = str(e)
                
        email_id = f"email-{uuid.uuid4()}"
        status = "SENT" if success else "OUTBOX"
        
        email_row = LocalEmail(
            email_id=email_id,
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
            sent_at=datetime.now(timezone.utc).isoformat() if success else None
        )
        
        session = self._get_db()
        try:
            session.add(email_row)
            session.commit()
            if success:
                logger.info("Email sent successfully: %s", subject)
            else:
                logger.warning("Mail provider offline. Email buffered in Outbox: %s", subject)
            return success
        finally:
            self._close_db(session)

    def list_drafts(self) -> list[dict[str, Any]]:
        return self._list_by_status("DRAFT")

    def list_outbox(self) -> list[dict[str, Any]]:
        return self._list_by_status("OUTBOX")

    def list_sent(self) -> list[dict[str, Any]]:
        return self._list_by_status("SENT")

    def preview_draft(self, draft_id: str) -> dict[str, Any]:
        session = self._get_db()
        try:
            row = session.query(LocalEmail).filter_by(email_id=draft_id).first()
            if not row:
                raise KeyError(f"Draft ID {draft_id} not found in database.")
            return self._row_to_dict(row)
        finally:
            self._close_db(session)

    def render_template(self, template_name: str, variables: dict[str, str]) -> str:
        """HTML simple template renderer helper."""
        template = TEMPLATES.get(template_name, "<html><body>{{ content }}</body></html>")
        rendered = template
        for k, v in variables.items():
            rendered = rendered.replace(f"{{{{ {k} }}}}", v)
        return rendered

    def _list_by_status(self, status: str) -> list[dict[str, Any]]:
        session = self._get_db()
        try:
            rows = session.query(LocalEmail).filter_by(status=status).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._close_db(session)

    def _row_to_dict(self, row: LocalEmail) -> dict[str, Any]:
        return {
            "draft_id": row.email_id,
            "recipient": row.recipient,
            "subject": row.subject,
            "html_content": row.html_content,
            "status": row.status,
            "template_name": row.template_name,
            "created_at": row.created_at,
            "sent_at": row.sent_at
        }
