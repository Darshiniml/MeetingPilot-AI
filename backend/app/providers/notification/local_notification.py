from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.provider_models import LocalNotification

logger = logging.getLogger(__name__)

class LocalNotificationProvider:
    """SQLite-backed notification provider maintaining alert records persistently in SQLite database."""
    
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
            "latency_ms": 2,
            "version": self.version,
            "capabilities": ["Read/Unread", "Severity", "Category", "Workflow_ref", "Meeting_ref"],
            "last_sync": self.last_sync,
            "error_info": self.error_info
        }

    def send_notification(
        self,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "INFO",
        workflow_id: str | None = None,
        meeting_id: int | None = None
    ) -> bool:
        """Create and store a persistent alert notification inside SQLite database."""
        notification_id = f"notif-{uuid.uuid4()}"
        notif = LocalNotification(
            notification_id=notification_id,
            title=title,
            message=message,
            category=category,
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_read=False,
            workflow_id=workflow_id,
            meeting_id=meeting_id
        )
        
        session = self._get_db()
        try:
            session.add(notif)
            session.commit()
            logger.info("Local SQLite Notification saved: %s - %s", title, message)
            return True
        finally:
            self._close_db(session)

    def list_notifications(
        self,
        is_read: bool | None = None,
        category: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve matching persistent alerts from SQLite database."""
        session = self._get_db()
        try:
            query = session.query(LocalNotification)
            if is_read is not None:
                query = query.filter_by(is_read=is_read)
            if category is not None:
                query = query.filter_by(category=category)
                
            rows = query.order_by(LocalNotification.timestamp.desc()).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._close_db(session)

    def mark_as_read(self, notification_id: str) -> None:
        session = self._get_db()
        try:
            row = session.query(LocalNotification).filter_by(notification_id=notification_id).first()
            if row:
                row.is_read = True
                session.commit()
                logger.info("Notification marked read: %s", notification_id)
        finally:
            self._close_db(session)

    def _row_to_dict(self, row: LocalNotification) -> dict[str, Any]:
        return {
            "notification_id": row.notification_id,
            "title": row.title,
            "message": row.message,
            "category": row.category,
            "severity": row.severity,
            "timestamp": row.timestamp,
            "is_read": row.is_read,
            "workflow_id": row.workflow_id,
            "meeting_id": row.meeting_id
        }
