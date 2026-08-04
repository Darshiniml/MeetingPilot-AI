"""Unit tests for the isolated milestone-one agent framework."""

import unittest

from app.agent.agent_controller import AgentController
from app.agent.conversation_store import ConversationStore
from app.agent.context import AgentContext
from app.agent.memory import ConversationMemory, WorkingMemory
from app.agent.memory_models import ConversationInteraction, ReflectionRecord
from app.agent.models import AgentIntent, AgentRequest, AgentResponse, ExecutionPlan, ToolExecution
from app.agent.planner import Planner
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.reflection import ReflectionEngine
from app.agent.registry import ToolRegistry
from app.agent.tools.scheduler_tool import SchedulerTool
from app.agent.tools.summary_tool import SummaryTool


class PlannerTests(unittest.TestCase):
    class FakeProvider:
        def __init__(self, *responses: str) -> None:
            self.responses = list(responses)
            self.prompts = []

        def generate(self, prompt: str):
            self.prompts.append(prompt)
            return type("Result", (), {"content": self.responses.pop(0)})()

    def test_parses_valid_json_multi_tool_plan(self) -> None:
        provider = self.FakeProvider(
            '{"intent":"MULTI_TOOL","confidence":0.97,"reasoning":"Schedule and notify.","tools":["contacts","calendar","gmail"],"parameters":{"person":"Rahul","date":"tomorrow"}}'
        )

        plan = Planner(provider=provider).plan("Schedule with Rahul tomorrow and notify him")

        self.assertEqual(plan.intent, AgentIntent.GENERAL_CHAT)
        self.assertEqual(plan.tools, ["contacts", "calendar", "gmail"])
        self.assertEqual(plan.parameters["person"], "Rahul")
        self.assertIn("Return ONLY valid JSON", provider.prompts[0])

    def test_planner_receives_memory_context(self) -> None:
        provider = self.FakeProvider(
            '{"intent":"GENERAL_CHAT","confidence":0.9,"reasoning":"follow-up","tools":["rag_chat"],"parameters":{}}'
        )

        Planner(provider=provider).plan("Schedule another", memory_context={"working_memory": {"duration": "30m"}})

        self.assertIn("duration", provider.prompts[0])

    def test_retries_once_with_repair_prompt(self) -> None:
        provider = self.FakeProvider(
            "this is not JSON",
            '{"intent":"SUMMARIZE_MEETING","confidence":0.9,"reasoning":"summary requested","tools":["summary"],"parameters":{}}',
        )

        plan = Planner(provider=provider).plan("Summarize meeting")

        self.assertEqual(plan.intent, AgentIntent.SUMMARIZE_MEETING)
        self.assertEqual(len(provider.prompts), 2)
        self.assertIn("Repair", provider.prompts[1])

    def test_invalid_retry_and_low_confidence_fall_back_to_general_chat(self) -> None:
        invalid_provider = self.FakeProvider("not json", "still not json")
        low_confidence_provider = self.FakeProvider(
            '{"intent":"SUMMARIZE_MEETING","confidence":0.2,"reasoning":"uncertain","tools":["summary"],"parameters":{}}'
        )

        self.assertEqual(Planner(provider=invalid_provider).plan("Hello").tools, ["rag_chat"])
        self.assertEqual(Planner(provider=low_confidence_provider).plan("Hello").intent, AgentIntent.GENERAL_CHAT)


class RegistryTests(unittest.TestCase):
    def test_auto_registers_all_agent_tools(self) -> None:
        registry = ToolRegistry()

        self.assertEqual(
            set(registry.list_tools()),
            {
                "summary", "transcript", "meeting_history", "action_items", "scheduler",
                "calendar", "gmail", "contacts", "rag_chat", "vision",
            },
        )

    def test_register_get_execute_and_unregister_tool(self) -> None:
        registry = ToolRegistry()

        def echo(*, context: AgentContext, user_message: str):
            return f"{context.current_user}: {user_message}"

        registry.register("echo", echo)
        self.assertIn("echo", registry.list_tools())
        self.assertIs(registry.get_tool("echo"), echo)
        result = registry.execute("echo", AgentContext(current_user=9), user_message="Hi")
        self.assertEqual(result, "9: Hi")
        self.assertIs(registry.unregister("echo"), echo)
        self.assertNotIn("echo", registry.list_tools())
        self.assertIn("summary", registry.list_tools())


class ControllerTests(unittest.TestCase):
    def test_controller_returns_structured_response(self) -> None:
        class FakeSummaryService:
            def generate_for_meeting(self, meeting_id: int):
                return {"meeting_id": meeting_id, "summary": "Ready"}

        registry = ToolRegistry(services={"summary": FakeSummaryService()})
        planner = type("FixedPlanner", (), {"plan": lambda _self, _message, memory_context=None: ExecutionPlan(intent=AgentIntent.SUMMARIZE_MEETING, confidence=1.0, tools=["summary"], reasoning="test", parameters={})})()

        response = AgentController(planner=planner, registry=registry).handle(
            AgentRequest(user_message="Please create a summary", user_id=4, meeting_id=12)
        )

        self.assertIsInstance(response, AgentResponse)
        self.assertEqual(response.execution_plan.intent, AgentIntent.SUMMARIZE_MEETING)
        self.assertEqual(response.tool_executions[0].status, "completed")
        self.assertEqual(response.tool_executions[0].output["summary"], "Ready")
        self.assertGreaterEqual(response.total_execution_time, 0)


class ToolAdapterTests(unittest.TestCase):
    def test_summary_tool_delegates_to_summary_service(self) -> None:
        class FakeSummaryService:
            def __init__(self) -> None:
                self.meeting_id = None

            def generate_for_meeting(self, meeting_id: int):
                self.meeting_id = meeting_id
                return "summary output"

        service = FakeSummaryService()
        output = SummaryTool(service).execute(AgentContext(current_user=1, active_meeting=21), {})

        self.assertEqual(service.meeting_id, 21)
        self.assertEqual(output, "summary output")

    def test_scheduler_tool_delegates_to_scheduler_service(self) -> None:
        class FakeSchedulerService:
            def __init__(self) -> None:
                self.calls = []

            def plan_meeting(self, request_text: str, user_id: int):
                self.calls.append((request_text, user_id))
                return "scheduled"

        service = FakeSchedulerService()
        output = SchedulerTool(service).execute(
            AgentContext(current_user=3), {"user_message": "Schedule lunch"}
        )

        self.assertEqual(service.calls, [("Schedule lunch", 3)])
        self.assertEqual(output, "scheduled")

    def test_registry_executes_multiple_tools_in_order(self) -> None:
        calls = []
        registry = ToolRegistry()
        registry.register("first", lambda *, context, **_parameters: calls.append(("first", context.current_user)) or 1)
        registry.register("second", lambda *, context, **_parameters: calls.append(("second", context.current_user)) or 2)

        results = registry.execute_tools(["first", "second"], AgentContext(current_user=8))

        self.assertEqual(results, [1, 2])
        self.assertEqual(calls, [("first", 8), ("second", 8)])

    def test_reasoning_engine_passes_earlier_tool_outputs_to_later_tools(self) -> None:
        registry = ToolRegistry()
        registry.register("contacts", lambda *, context, **_parameters: {"email": "rahul@example.com"})
        registry.register("gmail", lambda *, context, to_email, **_parameters: {"sent_to": to_email})
        plan = ExecutionPlan(
            intent=AgentIntent.GENERAL_CHAT,
            confidence=1.0,
            tools=["contacts", "gmail"],
            reasoning="test sequential flow",
            parameters={"to_email": "{{tool_outputs.contacts.email}}"},
        )

        executions, state = ReasoningEngine(registry).execute(plan, AgentContext(current_user=8))

        self.assertEqual([item.status for item in executions], ["completed", "completed"])
        self.assertEqual(executions[1].output, {"sent_to": "rahul@example.com"})
        self.assertEqual(state.tool_outputs["contacts"]["email"], "rahul@example.com")

    def test_reasoning_engine_updates_working_memory(self) -> None:
        registry = ToolRegistry()
        registry.register("contacts", lambda *, context, **_parameters: {"email": "rahul@example.com"})
        plan = ExecutionPlan(intent=AgentIntent.CONTACT_SEARCH, confidence=1.0, tools=["contacts"], reasoning="test", parameters={})
        memory = WorkingMemory()

        ReasoningEngine(registry).execute(plan, AgentContext(current_user=8), working_memory=memory)

        self.assertEqual(memory.resolved_contacts["email"], "rahul@example.com")


class MemoryTests(unittest.TestCase):
    @staticmethod
    def _interaction(message: str) -> ConversationInteraction:
        return ConversationInteraction(
            user_message=message,
            planner_decision={},
            agent_response="answer",
            reflection=ReflectionRecord(reflection="ok", confidence_adjustment=0.0),
        )

    def test_conversation_memory_is_bounded_and_retrievable(self) -> None:
        memory = ConversationMemory("conversation-1")
        for index in range(21):
            memory.add(self._interaction(f"Schedule project {index}"))

        retrieved = memory.retrieve("project")

        self.assertEqual(len(memory.interactions), 20)
        self.assertEqual(retrieved[0].user_message, "Schedule project 20")

    def test_reflection_reports_success_and_failures(self) -> None:
        plan = ExecutionPlan(intent=AgentIntent.GENERAL_CHAT, confidence=1.0, tools=["rag_chat"], reasoning="test", parameters={})
        success = ReflectionEngine().reflect(plan, [ToolExecution(tool_name="rag_chat", status="completed", execution_time_ms=1, output="ok")])
        failed = ReflectionEngine().reflect(plan, [ToolExecution(tool_name="rag_chat", status="failed", execution_time_ms=1, output="error")])

        self.assertGreater(success.confidence_adjustment, 0)
        self.assertLess(failed.confidence_adjustment, 0)


if __name__ == "__main__":
    unittest.main()
