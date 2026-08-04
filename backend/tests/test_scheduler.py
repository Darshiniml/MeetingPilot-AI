"""Tests for the AI Meeting Scheduler."""

import pytest
from app.scheduler.schemas import MeetingDetails
from app.scheduler.meeting_parser import MeetingParser, MeetingParserError
from app.scheduler.email_draft_service import EmailDraftService
from app.scheduler.scheduler_service import SchedulerService
from app.scheduler.calendar_service import MockCalendarProvider
from app.ai.providers import LLMResult

class MockLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        
    def generate(self, prompt: str) -> LLMResult:
        response = self.responses[self.calls]
        self.calls += 1
        return LLMResult(content=response)

def test_meeting_parser_success():
    llm = MockLLM(['```json\n{"title": "Sync", "date": "2023-10-10", "time": "10:00", "duration": "1h", "timezone": "UTC", "attendees": ["Alice"]}\n```'])
    parser = MeetingParser(llm)
    details = parser.parse("Schedule a Sync with Alice on Oct 10 at 10 AM")
    assert details.title == "Sync"
    assert details.attendees == ["Alice"]

def test_meeting_parser_retry_success():
    llm = MockLLM(['invalid json', '{"title": "Sync", "date": "2023-10-10", "time": "10:00", "duration": "1h", "timezone": "UTC", "attendees": []}'])
    parser = MeetingParser(llm)
    details = parser.parse("Schedule a Sync")
    assert details.title == "Sync"
    assert llm.calls == 2

def test_meeting_parser_retry_failure():
    llm = MockLLM(['invalid json', 'still invalid'])
    parser = MeetingParser(llm)
    with pytest.raises(MeetingParserError):
        parser.parse("Schedule a Sync")

def test_email_draft_service():
    llm = MockLLM(['Draft email output'])
    service = EmailDraftService(llm)
    details = MeetingDetails(title="Sync", date="Today", time="Now", duration="1h", timezone="UTC", attendees=[])
    draft = service.generate_draft(details)
    assert draft == 'Draft email output'

def test_scheduler_service():
    from unittest.mock import MagicMock
    llm = MockLLM([
        '{"title": "Sync", "date": "2023-10-10", "time": "10:00", "duration": "1h", "timezone": "UTC", "attendees": []}',
        'Draft output'
    ])
    service = SchedulerService(
        session=MagicMock(),
        parser=MeetingParser(llm),
        email_service=EmailDraftService(llm),
        calendar_provider=MockCalendarProvider(),
        email_provider=MagicMock()
    )
    plan = service.plan_meeting("Schedule a Sync")
    assert plan.title == "Sync"
    assert plan.email_draft == "Draft output"
    assert plan.calendar_preview.available is True
