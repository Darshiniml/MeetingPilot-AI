"""Unit tests for the Google Calendar integration."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from app.database.base import Base
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.models.google_calendar_token import GoogleCalendarToken
from app.integrations.google_calendar.token_store import TokenStore
from app.integrations.google_calendar.oauth import GoogleOAuthService
from app.integrations.google_calendar.calendar_provider import GoogleCalendarProvider, parse_meeting_time
from app.scheduler.schemas import MeetingDetails

# Setup SQLite in-memory database for testing
@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        # Create a test user
        user = User(id=1, name="Test User", email="test@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        yield session
    finally:
        session.close()

def test_token_store_encryption(db_session):
    store = TokenStore(db_session)
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Save tokens (which must trigger encryption)
    store.save_token(
        user_id=1,
        google_email="user@gmail.com",
        access_token="plain-access",
        refresh_token="plain-refresh",
        expires_at=expiry
    )
    
    # Query database directly to confirm encryption
    db_token = db_session.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == 1).first()
    assert db_token.access_token != "plain-access"
    assert db_token.refresh_token != "plain-refresh"
    assert "plain" not in db_token.access_token
    
    # Verify decryption
    decrypted = store.get_decrypted_tokens(user_id=1)
    assert decrypted["access_token"] == "plain-access"
    assert decrypted["refresh_token"] == "plain-refresh"
    assert decrypted["google_email"] == "user@gmail.com"

def test_oauth_url_generation():
    service = GoogleOAuthService()
    url = service.get_authorization_url(state="my-state")
    assert "client_id=" in url
    assert "state=my-state" in url
    assert "redirect_uri=" in url

@patch("httpx.Client.post")
@patch("httpx.Client.get")
def test_oauth_code_exchange(mock_get, mock_post):
    # Mock /token endpoint response
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "acc", "refresh_token": "ref", "expires_in": 3600}
    )
    # Mock /userinfo endpoint response
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"email": "user@gmail.com"}
    )
    
    service = GoogleOAuthService()
    tokens = service.exchange_code_for_tokens("mock-code")
    assert tokens["google_email"] == "user@gmail.com"
    assert tokens["access_token"] == "acc"
    assert tokens["refresh_token"] == "ref"

@patch("httpx.Client.post")
def test_oauth_refresh(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "new-acc", "expires_in": 3600}
    )
    
    service = GoogleOAuthService()
    refreshed = service.refresh_access_token("ref-token")
    assert refreshed["access_token"] == "new-acc"

def test_parse_meeting_time():
    now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc) # Saturday Aug 1, 2026
    
    # Test ISO date + 24h time
    start, end = parse_meeting_time("2026-08-05", "14:30", "1h", now=now)
    assert start.date() == datetime(2026, 8, 5).date()
    assert start.hour == 14
    assert start.minute == 30
    assert (end - start) == timedelta(hours=1)

    # Test "tomorrow" + AM/PM time
    start, end = parse_meeting_time("tomorrow", "2 PM", "30m", now=now)
    assert start.date() == datetime(2026, 8, 2).date()
    assert start.hour == 14
    assert start.minute == 0
    assert (end - start) == timedelta(minutes=30)

    # Test "next tuesday" + AM/PM
    start, end = parse_meeting_time("next tuesday", "11:30 am", "2h", now=now)
    assert start.weekday() == 1 # Tuesday
    assert start.date() == datetime(2026, 8, 4).date()
    assert start.hour == 11
    assert start.minute == 30

@patch("httpx.Client.post")
def test_calendar_check_availability_free(mock_post, db_session):
    # Store token in database
    store = TokenStore(db_session)
    store.save_token(
        user_id=1,
        google_email="user@gmail.com",
        access_token="acc",
        refresh_token="ref",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    # Mock FreeBusy endpoint with empty busy times (available)
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"calendars": {"primary": {"busy": []}}}
    )

    provider = GoogleCalendarProvider(db_session, user_id=1)
    details = MeetingDetails(title="Sync", date="2026-08-05", time="14:00", duration="1h", timezone="UTC", attendees=[])
    preview = provider.check_availability(details)
    
    assert preview.available is True
    assert len(preview.conflicts) == 0

@patch("httpx.Client.post")
def test_calendar_check_availability_conflict(mock_post, db_session):
    store = TokenStore(db_session)
    store.save_token(
        user_id=1,
        google_email="user@gmail.com",
        access_token="acc",
        refresh_token="ref",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    # Mock FreeBusy returning conflict (busy from 14:00 to 15:00 UTC)
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "calendars": {
                "primary": {
                    "busy": [{"start": "2026-08-05T14:00:00Z", "end": "2026-08-05T15:00:00Z"}]
                }
            }
        }
    )

    provider = GoogleCalendarProvider(db_session, user_id=1)
    details = MeetingDetails(title="Sync", date="2026-08-05", time="14:00", duration="1h", timezone="UTC", attendees=[])
    preview = provider.check_availability(details)
    
    assert preview.available is False
    assert len(preview.conflicts) > 0
    # Suggestions should be generated (e.g. 15:30, 16:00, etc.)
    assert len(preview.suggestions) > 0

@patch("httpx.Client.post")
def test_calendar_create_event(mock_post, db_session):
    store = TokenStore(db_session)
    store.save_token(
        user_id=1,
        google_email="user@gmail.com",
        access_token="acc",
        refresh_token="ref",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    # Mock Google Calendar event creation response
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "id": "event123",
            "htmlLink": "https://calendar.google.com/event",
            "conferenceData": {
                "entryPoints": [{"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"}]
            }
        }
    )

    provider = GoogleCalendarProvider(db_session, user_id=1)
    details = MeetingDetails(title="Sync Meeting", date="2026-08-05", time="10:00", duration="1h", timezone="UTC", attendees=[])
    event = provider.create_event(details)
    
    assert event["event_id"] == "event123"
    assert event["calendar_link"] == "https://calendar.google.com/event"
    assert event["google_meet_link"] == "https://meet.google.com/abc-defg-hij"
