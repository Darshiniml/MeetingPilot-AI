"""Tests for the additive supervisor and specialized-agent architecture."""

import unittest

from app.agent.models import AgentRequest
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.registry import ToolRegistry
from app.agents.agent_context import AgentContext
from app.agents.agent_messages import AgentMessage
from app.agents.agent_registry import AgentRegistry
from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.supervisor_agent import SupervisorAgent


class MultiAgentTests(unittest.TestCase):
    def _context(self):
        tools = ToolRegistry()
        for name in ("contacts", "scheduler", "calendar", "gmail", "summary", "transcript", "meeting_history", "action_items", "rag_chat"):
            tools.register(name, lambda *, context, _name=name, **_params: {"tool": _name, "user": context.current_user})
        return AgentContext(tool_registry=tools, reasoning_engine=ReasoningEngine(tools))

    def test_supervisor_routes_to_multiple_agents_and_merges_results(self):
        context = self._context()
        supervisor = SupervisorAgent(context)

        response = supervisor.handle(AgentRequest(user_message="Schedule a review meeting and send an email summary", user_id=3, meeting_id=7, conversation_id="c1"))

        self.assertIn("scheduler:", response.answer)
        self.assertIn("email:", response.answer)
        self.assertGreaterEqual(len(response.tool_executions), 4)
        self.assertGreater(context.metrics.handoffs, 0)

    def test_agent_messages_are_delivered_over_shared_event_bus(self):
        context = self._context()
        registry = AgentRegistry(context)

        registry.broadcast(AgentMessage(sender="supervisor", receiver="email", type="handoff", payload={"task": "draft"}, conversation_id="c2"), user_id=1)

        self.assertEqual(registry._agents["email"].inbox[0].payload["task"], "draft")
        self.assertEqual(registry._agents["meeting"].inbox, [])

    def test_agents_share_one_working_memory_store(self):
        context = self._context()
        registry = AgentRegistry(context)
        request = AgentRequest(user_message="Schedule a meeting", user_id=3, conversation_id="shared")

        registry._agents["scheduler"].execute(request)
        memory = context.conversation_store.get_working_memory("shared")

        self.assertIn("scheduler", memory.tool_outputs)
        self.assertIs(memory, context.conversation_store.get_working_memory("shared"))

    def test_supervisor_retries_failed_agent_once(self):
        context = self._context()
        registry = AgentRegistry(context, auto_register=False)

        class FlakyAgent(BaseAgent):
            keywords = ("flaky",)
            def __init__(self, ctx): super().__init__(ctx); self.calls = 0
            def name(self): return "flaky"
            def description(self): return "fails first time"
            def execute(self, request):
                self.calls += 1
                return AgentResult(self.name(), "ok" if self.calls == 2 else "failed", failed=self.calls == 1)

        flaky = FlakyAgent(context)
        registry.register(flaky)
        response = SupervisorAgent(context, registry).handle(AgentRequest(user_message="flaky task", user_id=1))

        self.assertEqual(flaky.calls, 2)
        self.assertIn("flaky: ok", response.answer)


if __name__ == "__main__":
    unittest.main()
