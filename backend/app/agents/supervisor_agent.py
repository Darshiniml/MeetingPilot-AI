from __future__ import annotations

from time import perf_counter

from app.agent.models import AgentIntent, AgentRequest, AgentResponse, ExecutionPlan

from .agent_context import AgentContext
from .agent_messages import AgentMessage
from .agent_registry import AgentRegistry
from .base_agent import AgentResult, BaseAgent


class SupervisorAgent(BaseAgent):
    def __init__(self, context: AgentContext, registry: AgentRegistry | None = None) -> None:
        super().__init__(context)
        self.registry = registry or AgentRegistry(context)

    def name(self): return "supervisor"
    def description(self): return "Coordinates specialized agents and merges their results."
    def can_handle(self, request): return True

    def handle(self, request: AgentRequest) -> AgentResponse:
        started = perf_counter()
        agents = self.registry.find_capable_agents(request) or [self.registry._agents["research"]]
        results: list[AgentResult] = []
        for agent in agents:
            self.registry.broadcast(AgentMessage(sender=self.name(), receiver=agent.name(), type="handoff", payload={"request": request.user_message}, conversation_id=request.conversation_id), request.user_id, request.meeting_id)
            try:
                result = agent.execute(request)
                if result.failed:
                    result = agent.execute(request)  # one retry
                if result.failed:
                    alternative = next((candidate for candidate in agents if candidate.name() != agent.name()), None)
                    if alternative is not None:
                        self.registry.broadcast(AgentMessage(sender=self.name(), receiver=alternative.name(), type="recovery_handoff", payload={"request": request.user_message, "failed_agent": agent.name()}, conversation_id=request.conversation_id), request.user_id, request.meeting_id)
                        result = alternative.execute(request)
            except Exception as error:
                result = AgentResult(agent.name(), str(error), failed=True)
            results.append(result)
        executions = [execution for result in results for execution in result.executions]
        answer = "\n".join(f"{result.agent_name}: {result.answer}" for result in results)
        self.context.metrics.coordination_latency_ms += (perf_counter() - started) * 1000
        return AgentResponse(answer=answer, execution_plan=ExecutionPlan(intent=AgentIntent.GENERAL_CHAT, confidence=1.0, tools=[tool for agent in agents for tool in agent.tools], reasoning="Supervisor coordinated specialized agents.", parameters={}), tool_executions=executions, total_execution_time=(perf_counter() - started) * 1000)
