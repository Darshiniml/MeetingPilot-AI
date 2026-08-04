import unittest

from app.agent.events.autonomous_policy import AutonomousPolicy
from app.agent.events.event_models import MeetingStoppedEvent, SummaryGeneratedEvent, TranscriptSavedEvent


class AutonomousPolicyTests(unittest.TestCase):
    def test_meeting_stopped_requests_post_meeting_safe_work(self):
        decision = AutonomousPolicy().evaluate(MeetingStoppedEvent(user_id=1, meeting_id=4))
        self.assertTrue(decision.should_react)
        self.assertIn("summary", decision.message.casefold())

    def test_transcript_signal_is_actionable(self):
        decision = AutonomousPolicy().evaluate(TranscriptSavedEvent(user_id=1, payload={"text": "We decided Priya will follow up by Friday."}))
        self.assertTrue(decision.should_react)

    def test_summary_generated_updates_agent_memory_context(self):
        decision = AutonomousPolicy().evaluate(SummaryGeneratedEvent(user_id=1, meeting_id=4))
        self.assertTrue(decision.should_react)
        self.assertIn("memory", decision.message.casefold())
