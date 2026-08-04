"""Unit tests for the isolated event-driven autonomous agent layer."""

import unittest

from app.agent.events.agent_observer import AgentObserver
from app.agent.events.autonomous_policy import AutonomousPolicy
from app.agent.events.event_bus import EventBus
from app.agent.events.event_models import CalendarConflictEvent, MeetingStoppedEvent, TranscriptSavedEvent
from app.agent.models import AgentIntent, ExecutionPlan
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.registry import ToolRegistry


class FixedPlanner:
    def __init__(self, plan: ExecutionPlan) -> None:
        self.plan_to_return = plan
        self.calls = []

    def plan(self, message: str, memory_context=None) -> ExecutionPlan:
        self.calls.append((message, memory_context))
        return self.plan_to_return


class EventBusTests(unittest.TestCase):
    def test_publish_delivers_to_subscribers_in_subscription_order(self) -> None:
        bus = EventBus()
        received = []
        first = bus.subscribe(__import__("app.agent.events.event_types", fromlist=["EventType"]).EventType.MEETING_STOPPED, lambda event: received.append(("first", event.event_id)))
        bus.subscribe(__import__("app.agent.events.event_types", fromlist=["EventType"]).EventType.MEETING_STOPPED, lambda event: received.append(("second", event.event_id)))
        event = MeetingStoppedEvent(user_id=1, meeting_id=2)

        bus.publish(event)
        self.assertTrue(bus.unsubscribe(first))
        bus.publish(event)

        self.assertEqual(received, [("first", event.event_id), ("second", event.event_id), ("second", event.event_id)])


class AutonomousEventTests(unittest.TestCase):
    def _observer(self, plan: ExecutionPlan):
        registry = ToolRegistry()
        registry.register("summary", lambda *, context, **_params: {"meeting_id": context.active_meeting, "summary": "created"})
        registry.register("rag_chat", lambda *, context, **_params: "recommendation")
        return AgentObserver(FixedPlanner(plan), ReasoningEngine(registry))

    def test_meeting_stopped_triggers_safe_summary_execution(self) -> None:
        observer = self._observer(ExecutionPlan(intent=AgentIntent.SUMMARIZE_MEETING, confidence=1.0, tools=["summary"], reasoning="post meeting", parameters={}))

        result = observer.on_event(MeetingStoppedEvent(user_id=4, meeting_id=22))

        self.assertTrue(result.policy.should_react)
        self.assertEqual(result.executions[0].tool_name, "summary")
        self.assertEqual(result.executions[0].status, "completed")

    def test_transcript_signal_generates_agent_recommendation(self) -> None:
        observer = self._observer(ExecutionPlan(intent=AgentIntent.GENERAL_CHAT, confidence=1.0, tools=["rag_chat"], reasoning="risk found", parameters={}))

        result = observer.on_event(TranscriptSavedEvent(user_id=4, meeting_id=22, payload={"text": "Rahul will follow up by Friday."}))

        self.assertTrue(result.policy.should_react)
        self.assertIn("commitments", result.policy.message)
        self.assertEqual(result.executions[0].output, "recommendation")

    def test_calendar_conflict_creates_pending_approval_instead_of_execution(self) -> None:
        observer = self._observer(ExecutionPlan(intent=AgentIntent.GOOGLE_CALENDAR, confidence=1.0, tools=["calendar"], reasoning="find another slot", parameters={"date": "tomorrow"}))

        result = observer.on_event(CalendarConflictEvent(user_id=4, meeting_id=22))

        self.assertEqual(result.executions, [])
        self.assertEqual(len(result.pending_tasks), 1)
        self.assertEqual(result.pending_tasks[0].required_tool, "calendar")
        self.assertEqual(observer.pending_tasks.list("pending")[0].approval_status, "pending")

    def test_policy_ignores_non_actionable_transcript(self) -> None:
        decision = AutonomousPolicy().evaluate(TranscriptSavedEvent(user_id=4, payload={"text": "Hello everyone."}))

        self.assertFalse(decision.should_react)


if __name__ == "__main__":
    unittest.main()
