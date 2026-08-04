from __future__ import annotations

from sqlalchemy import Column, String, Text, Boolean, Integer
from app.database.base import Base

class ProviderConfig(Base):
    """Database backed configuration options for active provider switching."""
    __tablename__ = "provider_configs"
    key = Column(String(50), primary_key=True)
    value = Column(String(100), nullable=False)

class LocalCalendarEvent(Base):
    """Database backed local calendar database entries."""
    __tablename__ = "local_calendar_events"
    event_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    date = Column(String(20), nullable=False)
    time = Column(String(20), nullable=False)
    duration = Column(String(20), nullable=False)
    start_time = Column(String(50), nullable=False)
    end_time = Column(String(50), nullable=False)
    attendees_json = Column(Text, nullable=False, default="[]")
    is_recurring = Column(Boolean, nullable=False, default=False)
    recurrence_rule = Column(String(100), nullable=True)
    reminder_minutes_before = Column(Integer, nullable=False, default=15)

class LocalEmail(Base):
    """Database backed drafts, outbox, and sent email records."""
    __tablename__ = "local_emails"
    email_id = Column(String(50), primary_key=True)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    html_content = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="DRAFT") # DRAFT, OUTBOX, SENT
    template_name = Column(String(100), nullable=True)
    created_at = Column(String(50), nullable=False)
    sent_at = Column(String(50), nullable=True)

class LocalNotification(Base):
    """Database backed notification alerts center records."""
    __tablename__ = "local_notifications"
    notification_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="general")
    severity = Column(String(30), nullable=False, default="INFO") # INFO, WARNING, CRITICAL
    timestamp = Column(String(50), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    workflow_id = Column(String(50), nullable=True)
    meeting_id = Column(Integer, nullable=True)
