import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.scheduler.schemas import MeetingDetails
from app.providers import (
    ProviderManager,
    ProviderRegistry,
    get_calendar_provider,
    get_email_provider,
    get_notification_provider,
    get_storage_provider
)
from app.providers.calendar.local_calendar import LocalCalendarProvider
from app.providers.email.local_email import LocalEmailProvider
from app.providers.notification.local_notification import LocalNotificationProvider

@pytest.fixture
def mock_db():
    """Create clean memory SQLite database session for unit testing isolation."""
    engine = create_engine("sqlite:///:memory:")
    # import all models to resolve foreign keys on Base.metadata
    import app.models
    from app.models.user import User
    from app.memory.memory_models import Memory
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_dynamic_discovery():
    supported = ProviderRegistry.list_supported()
    assert "calendar" in supported
    assert "local" in supported["calendar"]
    assert "google" in supported["calendar"]
    assert "local" in supported["email"]
    assert "smtp" in supported["email"]

def test_sqlite_provider_switching_and_persistence(mock_db):
    # Setup ProviderManager active setup using mocked database session
    ProviderManager.set_active("calendar", "local", mock_db)
    config = ProviderManager.load_config(mock_db)
    assert config["calendar"] == "local"
    
    # Switch provider
    ProviderManager.set_active("calendar", "google", mock_db)
    config2 = ProviderManager.load_config(mock_db)
    assert config2["calendar"] == "google"

def test_local_calendar_sqlite_functionality(mock_db):
    calendar = LocalCalendarProvider(mock_db)
    
    # 1. Create Event
    details = MeetingDetails(
        title="Offline Planning Session",
        date="2026-08-04",
        time="10:00",
        duration="1h",
        attendees=["manager@company.com"]
    )
    
    # Bypass Pydantic schema validation for temporary test attributes
    object.__setattr__(details, "is_recurring", True)
    object.__setattr__(details, "recurrence_rule", "WEEKLY")
    object.__setattr__(details, "reminder_minutes", 30)
    
    # Check availability
    preview = calendar.check_availability(details)
    assert preview.available is True
    
    evt = calendar.create_event(details)
    assert evt["title"] == "Offline Planning Session"
    assert evt["is_recurring"] is True
    assert evt["recurrence_rule"] == "WEEKLY"
    assert evt["reminder_minutes"] == 30
    
    # 2. Check conflicts double booking
    conflict_details = MeetingDetails(
        title="Double Booked Meeting",
        date="2026-08-04",
        time="10:30",
        duration="30m",
        attendees=[]
    )
    preview_conflict = calendar.check_availability(conflict_details)
    assert preview_conflict.available is False
    assert len(preview_conflict.conflicts) > 0
    
    # 3. Day/Week/Month range query
    range_events = calendar.get_events_for_range("2026-08-01", "2026-08-10")
    assert len(range_events) == 1
    assert range_events[0]["title"] == "Offline Planning Session"
    
    # Out of range check
    range_events_empty = calendar.get_events_for_range("2026-09-01", "2026-09-10")
    assert len(range_events_empty) == 0

def test_local_mailbox_sqlite_persistence(mock_db):
    mailbox = LocalEmailProvider(mock_db)
    
    # 1. Save draft
    draft = mailbox.save_draft(
        recipient="partner@vendor.com",
        subject="Draft Roadmap",
        html_content="<b>Proposal document</b>",
        template_name="meeting_invitation"
    )
    assert draft["status"] == "DRAFT"
    assert draft["template_name"] == "meeting_invitation"
    
    assert len(mailbox.list_drafts()) == 1
    assert len(mailbox.list_outbox()) == 0
    assert len(mailbox.list_sent()) == 0
    
    # 2. Template rendering
    rendered = mailbox.render_template("meeting_invitation", {"title": "Design Sync", "date": "Aug 4", "time": "3 PM"})
    assert "Design Sync" in rendered
    assert "Aug 4" in rendered
    
    # 3. Send email fallback to local outbox when SMTP is not configured
    success = mailbox.send_draft(
        recipient="customer@care.com",
        subject="Immediate Inquiry",
        html_content="<p>Query details</p>"
    )
    assert success is False # SMTP inactive fallback to outbox queue
    
    assert len(mailbox.list_outbox()) == 1
    outbox_mail = mailbox.list_outbox()[0]
    assert outbox_mail["subject"] == "Immediate Inquiry"
    assert outbox_mail["status"] == "OUTBOX"

def test_notification_center_sqlite_persistence(mock_db):
    notifier = LocalNotificationProvider(mock_db)
    assert len(notifier.list_notifications()) == 0
    
    # Send notification with severity, category, workflow & meeting references
    notifier.send_notification(
        title="DAG Execution Finished",
        message="Workflow customer-sync finished successfully.",
        category="workflows",
        severity="WARNING",
        workflow_id="wf-100",
        meeting_id=12
    )
    
    notifs = notifier.list_notifications()
    assert len(notifs) == 1
    
    alert = notifs[0]
    assert alert["title"] == "DAG Execution Finished"
    assert alert["category"] == "workflows"
    assert alert["severity"] == "WARNING"
    assert alert["workflow_id"] == "wf-100"
    assert alert["meeting_id"] == 12
    assert alert["is_read"] is False
    
    # Mark read status
    notifier.mark_as_read(alert["notification_id"])
    
    read_notifs = notifier.list_notifications(is_read=True)
    assert len(read_notifs) == 1
    assert read_notifs[0]["is_read"] is True

def test_provider_health_monitoring(mock_db):
    calendar = LocalCalendarProvider(mock_db)
    h = calendar.get_health()
    assert h["status"] == "healthy"
    assert "timezone_scheduling" in h["capabilities"]
    assert "conflict_detection" in h["capabilities"]

@patch("smtplib.SMTP")
def test_automatic_fallback_proxy(mock_smtp, mock_db):
    # Configure provider configurations priority in db
    # Primary: smtp, Secondary: local (fallback)
    ProviderManager.set_active("email", "smtp", mock_db)
    
    # Simulate SMTP server failure
    mock_smtp.side_effect = Exception("SMTP Auth Failed")
    
    email_proxy = ProviderManager.get_email(mock_db, 1)
    
    # Call send_draft. The FallbackProxy should catch the Exception, switch active to "local",
    # instantiate LocalEmailProvider, and complete the write safely to the Outbox table.
    success = email_proxy.send_draft(
        recipient="ceo@company.com",
        subject="Critical Alert",
        html_content="System warning details"
    )
    
    assert success is False # local outbox returns false to indicate local queuing
    config = ProviderManager.load_config(mock_db)
    assert config["email"] == "local" # Switched to fallback provider
