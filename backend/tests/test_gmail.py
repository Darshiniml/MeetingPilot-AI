import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import httpx

from app.integrations.gmail.gmail_provider import GmailProvider
from app.integrations.gmail.email_templates import load_template
from app.scheduler.schemas import MeetingDetails
from app.models.google_calendar_token import GoogleCalendarToken
from app.models.meeting import Meeting
from app.models.email_log import EmailLog
from app.scheduler.scheduler_service import SchedulerService

from app.ai.providers import LLMResult

class MockLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str) -> LLMResult:
        res = self.responses[self.index]
        self.index = (self.index + 1) % len(self.responses)
        return LLMResult(content=res)

class GmailIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock()
        self.user_id = 1
        
        # Setup decrypted token data mock
        self.token_record = GoogleCalendarToken(
            user_id=self.user_id,
            google_email="test@gmail.com",
            access_token="encrypted_access",
            refresh_token="encrypted_refresh",
            scopes="https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/gmail.send",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_connected=True
        )
        
        self.session.query().filter_by().first.return_value = self.token_record
        self.session.get.return_value = self.token_record
        
    @patch("app.integrations.google_calendar.token_store.TokenStore.get_decrypted_tokens")
    @patch("app.integrations.google_calendar.token_store.TokenStore.get_token")
    @patch("httpx.Client.post")
    def test_gmail_provider_send_html_email_success(self, mock_post, mock_get_token, mock_decrypted) -> None:
        mock_decrypted.return_value = {
            "google_email": "test@gmail.com",
            "access_token": "valid_token",
            "refresh_token": "valid_refresh",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        mock_get_token.return_value = self.token_record
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg123", "threadId": "thread123"}
        mock_post.return_value = mock_response
        
        provider = GmailProvider(self.session, self.user_id)
        result = provider.send_html_email(
            to_email="recipient@gmail.com",
            subject="Test Subject",
            html_body="<h1>Hello</h1>",
            meeting_id=10
        )
        
        self.assertEqual(result["message_id"], "msg123")
        self.assertEqual(result["thread_id"], "thread123")
        
        # Verify db log call
        self.session.add.assert_called_once()
        added_log = self.session.add.call_args[0][0]
        self.assertIsInstance(added_log, EmailLog)
        self.assertEqual(added_log.status, "SENT")
        self.assertEqual(added_log.meeting_id, 10)
        self.assertEqual(added_log.recipient, "recipient@gmail.com")

    @patch("app.integrations.google_calendar.token_store.TokenStore.get_decrypted_tokens")
    @patch("app.integrations.google_calendar.token_store.TokenStore.get_token")
    def test_gmail_provider_raises_error_if_scopes_missing(self, mock_get_token, mock_decrypted) -> None:
        token_without_gmail = GoogleCalendarToken(
            user_id=self.user_id,
            google_email="test@gmail.com",
            access_token="encrypted_access",
            refresh_token="encrypted_refresh",
            scopes="https://www.googleapis.com/auth/calendar", # Gmail scope is missing
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_connected=True
        )
        mock_get_token.return_value = token_without_gmail
        mock_decrypted.return_value = {
            "google_email": "test@gmail.com",
            "access_token": "valid_token",
            "refresh_token": "valid_refresh",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        provider = GmailProvider(self.session, self.user_id)
        with self.assertRaises(RuntimeError) as context:
            provider.send_email("to@example.com", "Subj", "Body")
        self.assertIn("gmail.send", str(context.exception))

    def test_email_html_template_rendering(self) -> None:
        details = MeetingDetails(
            title="Design Review",
            date="2026-08-10",
            time="14:00",
            duration="45m",
            timezone="EST",
            attendees=["one@test.com"]
        )
        
        html = load_template(
            template_name="invitation",
            details=details,
            meet_link="https://meet.google.com/abc-defg-hij",
            body_content="Draft agenda description goes here."
        )
        
        self.assertIn("Design Review", html)
        self.assertIn("2026-08-10", html)
        self.assertIn("14:00", html)
        self.assertIn("https://meet.google.com/abc-defg-hij", html)
        self.assertIn("Draft agenda description goes here.", html)

    @patch("app.integrations.google_calendar.token_store.TokenStore.get_decrypted_tokens")
    @patch("app.integrations.google_calendar.token_store.TokenStore.get_token")
    @patch("httpx.Client.post")
    def test_gmail_provider_transient_retry_logic(self, mock_post, mock_get_token, mock_decrypted) -> None:
        mock_decrypted.return_value = {
            "google_email": "test@gmail.com",
            "access_token": "valid_token",
            "refresh_token": "valid_refresh",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        mock_get_token.return_value = self.token_record
        
        # Setup transient failures (503 Service Unavailable) then success
        resp_503 = MagicMock()
        resp_503.status_code = 503
        resp_503.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="503 Service Unavailable",
            request=MagicMock(),
            response=resp_503
        )
        
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"id": "msg999", "threadId": "thread999"}
        
        mock_post.side_effect = [resp_503, resp_503, resp_200]
        
        provider = GmailProvider(self.session, self.user_id)
        # Mock sleep to run tests fast
        with patch("time.sleep") as mock_sleep:
            result = provider.send_html_email("to@example.com", "Subject", "Body")
            self.assertEqual(result["message_id"], "msg999")
            self.assertEqual(mock_sleep.call_count, 2)

    @patch("app.integrations.google_calendar.token_store.TokenStore.get_decrypted_tokens")
    @patch("app.integrations.google_calendar.token_store.TokenStore.get_token")
    @patch("httpx.Client.post")
    def test_gmail_provider_failure_logged_in_db(self, mock_post, mock_get_token, mock_decrypted) -> None:
        mock_decrypted.return_value = {
            "google_email": "test@gmail.com",
            "access_token": "valid_token",
            "refresh_token": "valid_refresh",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        mock_get_token.return_value = self.token_record
        
        # Permanent failure
        resp_400 = MagicMock()
        resp_400.status_code = 400
        resp_400.text = "Bad Request payload"
        mock_post.return_value = resp_400
        
        provider = GmailProvider(self.session, self.user_id)
        with self.assertRaises(RuntimeError):
            provider.send_html_email("to@example.com", "Subject", "Body", meeting_id=45)
            
        # Verify db log logged FAILED status
        self.session.add.assert_called_once()
        added_log = self.session.add.call_args[0][0]
        self.assertEqual(added_log.status, "FAILED")
        self.assertIn("Bad Request payload", added_log.error_message)

    @patch("app.scheduler.calendar_service.MockCalendarProvider.create_event")
    @patch("app.integrations.gmail.gmail_provider.GmailProvider.send_html_email")
    def test_scheduler_service_sends_invitations_automatically(self, mock_send, mock_calendar_create) -> None:
        # Mock Google Meet link creation
        mock_calendar_create.return_value = {
            "event_id": "google_event_789",
            "calendar_link": "https://calendar.google.com/event",
            "google_meet_link": "https://meet.google.com/xyz"
        }
        
        mock_send.return_value = {"message_id": "gmsg_101", "thread_id": "gthread_101"}
        
        meeting_record = Meeting(id=5, title="Team Sync", user_id=self.user_id)
        self.session.get.return_value = meeting_record
        
        llm = MockLLM(["Draft agenda text [Insert Meeting Link Here]"])
        from app.scheduler.meeting_parser import MeetingParser
        from app.scheduler.email_draft_service import EmailDraftService
        from app.scheduler.calendar_service import MockCalendarProvider
        
        service = SchedulerService(
            session=self.session,
            parser=MeetingParser(llm),
            email_service=EmailDraftService(llm),
            calendar_provider=MockCalendarProvider(),
            email_provider=GmailProvider(self.session, self.user_id)
        )
        
        details = MeetingDetails(
            title="Team Sync",
            date="2026-08-05",
            time="11:00",
            duration="1h",
            timezone="UTC",
            attendees=["user1@test.com", "user2@test.com"]
        )
        
        service.create_meeting_event(user_id=self.user_id, details=details, meeting_id=5)
        
        # Verify event creation was recorded
        self.assertEqual(meeting_record.google_event_id, "google_event_789")
        self.assertEqual(meeting_record.google_meet_link, "https://meet.google.com/xyz")
        
        # Verify Gmail invite was sent and fields set on Meeting model
        self.assertEqual(meeting_record.gmail_message_id, "gmsg_101")
        self.assertEqual(meeting_record.gmail_thread_id, "gthread_101")
        self.assertEqual(meeting_record.invitation_status, "SENT")
        self.assertIsNotNone(meeting_record.invitation_sent_at)
        
        # Assert send email was called twice (once for each attendee)
        self.assertEqual(mock_send.call_count, 2)
