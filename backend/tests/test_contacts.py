import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Any
import httpx

from app.contacts.contact_model import Contact
from app.models.user import User
from app.contacts.contact_repository import ContactRepository
from app.contacts.contact_matcher import ContactMatcher
from app.contacts.contact_service import ContactService
from app.scheduler.schemas import MeetingDetails
from app.scheduler.scheduler_service import SchedulerService

class MockLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str) -> Any:
        # Mock LLMResult
        from app.ai.providers import LLMResult
        res = self.responses[self.index]
        self.index = (self.index + 1) % len(self.responses)
        return LLMResult(content=res)

class ContactIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock()
        self.user_id = 1
        self.repo = ContactRepository(self.session, self.user_id)
        self.matcher = ContactMatcher(self.repo)
        
        # Sample contacts list
        self.alice = Contact(
            id=101,
            user_id=self.user_id,
            display_name="Alice Vance",
            first_name="Alice",
            last_name="Vance",
            company="Acme Corp",
            job_title="Design Engineer",
            email="alice@acme.com",
            phone="111-222-3333",
            linkedin_url="https://linkedin.com/in/alice-vance",
            is_favorite=True,
            notes="Key designer"
        )
        self.bob = Contact(
            id=102,
            user_id=self.user_id,
            display_name="Bob Miller",
            first_name="Bob",
            last_name="Miller",
            company="Globex",
            email="bob@globex.com"
        )
        self.alice_globex = Contact(
            id=103,
            user_id=self.user_id,
            display_name="Alice Smith",
            first_name="Alice",
            last_name="Smith",
            company="Globex",
            email="asmith@globex.com"
        )

    def test_exact_name_matching(self) -> None:
        contacts = [self.alice, self.bob]
        res = self.matcher.resolve_attendee("Alice Vance", contacts)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["resolved_email"], "alice@acme.com")
        self.assertGreaterEqual(res["confidence_score"], 0.70)

    def test_fuzzy_name_matching(self) -> None:
        contacts = [self.alice, self.bob]
        res = self.matcher.resolve_attendee("Alise", contacts)
        # "Alise" should match "Alice Vance" (specifically "Alice" first_name is close)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["resolved_email"], "alice@acme.com")
        self.assertGreaterEqual(res["confidence_score"], 0.60)

    def test_company_aware_boosting(self) -> None:
        # Two Alices exist: Alice Vance (Acme Corp) and Alice Smith (Globex)
        contacts = [self.alice, self.alice_globex]
        
        # Without company context, it should be ambiguous
        res = self.matcher.resolve_attendee("Alice", contacts)
        self.assertEqual(res["status"], "AMBIGUOUS")
        self.assertIsNone(res["resolved_email"])
        
        # With Globex context, Globex Alice gets company match score boost and resolves uniquely
        res_with_company = self.matcher.resolve_attendee(
            "Alice",
            contacts,
            context_text="Schedule a sync with Alice from Globex next Monday"
        )
        self.assertEqual(res_with_company["status"], "RESOLVED")
        self.assertEqual(res_with_company["resolved_email"], "asmith@globex.com")

    @patch("app.contacts.contact_repository.ContactRepository.get_invitation_frequency")
    def test_weighted_meeting_frequency_boosting(self, mock_freq) -> None:
        # Two Alices exist
        contacts = [self.alice, self.alice_globex]
        
        # Mock high meeting frequency for Alice Vance
        def get_freq(email):
            return 12 if email == "alice@acme.com" else 0
        mock_freq.side_effect = get_freq
        
        # Querying just "Alice" should now resolve to Alice Vance due to historical frequency boost
        res = self.matcher.resolve_attendee("Alice", contacts)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["resolved_email"], "alice@acme.com")

    def test_csv_import_mappings_and_duplicates(self) -> None:
        csv_data = (
            "Name,First Name,Last Name,Company,Job Title,Email,Phone,Notes\n"
            "Charlie Prince,Charlie,Prince,Zeta Inc,VP Sales,charlie@zeta.com,444-555,Test Note\n"
            "Alice Vance,Alice,Vance,Acme Corp,Designer,alice@acme.com,111-222,New Custom Note\n"
        )
        
        service = ContactService(self.session, self.user_id)
        
        # Mock existing record lookup
        def mock_get_email(email):
            return self.alice if email == "alice@acme.com" else None
        
        with patch.object(service.repo, "get_contact_by_email", side_effect=mock_get_email), \
             patch.object(service.repo, "create_contact") as mock_create, \
             patch.object(service.repo, "update_contact") as mock_update:
                 
            results = service.import_contacts_csv(csv_data)
            
            # Charlie created
            mock_create.assert_called_once()
            created_contact = mock_create.call_args[0][0]
            self.assertEqual(created_contact.display_name, "Charlie Prince")
            self.assertEqual(created_contact.email, "charlie@zeta.com")
            
            # Alice merged (already existed, fields updated, is_favorite preserved)
            mock_update.assert_called_once()
            self.assertEqual(self.alice.is_favorite, True) # local edit preserved

    @patch("app.contacts.contact_service.ContactService._get_google_access_token")
    @patch("httpx.Client.get")
    def test_google_contacts_sync_with_merge_conflict_prevention(self, mock_get, mock_token) -> None:
        mock_token.return_value = "google_token"
        
        # Mock Google People API connections list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "connections": [
                {
                    "names": [{"displayName": "Alice Vance", "givenName": "Alice", "familyName": "Vance"}],
                    "emailAddresses": [{"value": "alice@acme.com"}],
                    "phoneNumbers": [{"value": "888-888-8888"}],
                    "organizations": [{"name": "Acme Corp", "title": "Lead Architect"}],
                    "biographies": [{"value": "Google Note details"}]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        service = ContactService(self.session, self.user_id)
        
        with patch.object(service.repo, "get_contact_by_email", return_value=self.alice), \
             patch.object(service.repo, "update_contact") as mock_update:
                 
            # Set a manually modified local linkedin url
            self.alice.linkedin_url = "https://custom-linkedin.com"
            
            service.sync_google_contacts()
            
            # Verify update was called to merge rather than blind overwrite
            mock_update.assert_called_once()
            
            # Local linkedin url remains untouched
            self.assertEqual(self.alice.linkedin_url, "https://custom-linkedin.com")
            # Google phone was written since local phone was empty? (Local phone was '111-222-3333' in setUp, so it shouldn't overwrite)
            self.assertEqual(self.alice.phone, "111-222-3333")
            # Google notes merged by appending
            self.assertIn("Google Note details", self.alice.notes)
            self.assertIn("Key designer", self.alice.notes)

    @patch("app.scheduler.calendar_service.MockCalendarProvider.check_availability")
    @patch("app.scheduler.email_draft_service.EmailDraftService.generate_draft")
    @patch("app.contacts.contact_repository.ContactRepository.list_contacts")
    def test_scheduler_service_resolves_attendees_automatically(self, mock_list, mock_draft, mock_avail) -> None:
        mock_list.return_value = [self.alice, self.bob]
        mock_draft.return_value = "Draft Text"
        
        from app.scheduler.schemas import CalendarPreview
        mock_avail.return_value = CalendarPreview(
            provider="mock",
            available=True,
            conflicts=[],
            suggestions=[]
        )
    
        llm = MockLLM(['{"title": "Sync", "date": "2026-10-10", "time": "10:00", "duration": "1h", "timezone": "UTC", "attendees": ["Alice"]}'])
        
        from app.scheduler.meeting_parser import MeetingParser
        from app.scheduler.email_draft_service import EmailDraftService
        from app.scheduler.calendar_service import MockCalendarProvider
        
        service = SchedulerService(
            session=self.session,
            parser=MeetingParser(llm),
            email_service=EmailDraftService(llm),
            calendar_provider=MockCalendarProvider(),
            email_provider=MagicMock()
        )
        
        # Run plan meeting with user context (resolves 'Alice' to 'alice@acme.com')
        plan = service.plan_meeting("Schedule a Sync with Alice", user_id=self.user_id)
        
        # Verify attendees email was resolved correctly
        self.assertEqual(plan.attendees, ["alice@acme.com"])
        
        # Verify structured resolutions list
        self.assertEqual(len(plan.attendee_resolutions), 1)
        resolution = plan.attendee_resolutions[0]
        self.assertEqual(resolution.input_name, "Alice")
        self.assertEqual(resolution.resolved_email, "alice@acme.com")
        self.assertEqual(resolution.status, "RESOLVED")
        self.assertEqual(resolution.source, "CONTACTS")
        self.assertGreaterEqual(resolution.confidence_score, 0.70)
