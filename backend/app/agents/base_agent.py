from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.agent.context import AgentContext as ToolContext
from app.agent.models import AgentIntent, AgentRequest, ExecutionPlan, ToolExecution

from .agent_context import AgentContext
from .agent_messages import AgentMessage


@dataclass
class AgentResult:
    agent_name: str
    answer: str
    executions: list[ToolExecution] = field(default_factory=list)
    failed: bool = False


class BaseAgent(ABC):
    """Common specialization boundary; tools remain the only capability layer."""
    tools: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()

    def __init__(self, context: AgentContext) -> None:
        self.context = context
        self.inbox: list[AgentMessage] = []

    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def description(self) -> str: ...

    def can_handle(self, request: AgentRequest) -> bool:
        message = request.user_message.casefold()
        return any(keyword in message for keyword in self.keywords)

    def plan(self, request: AgentRequest) -> ExecutionPlan:
        return ExecutionPlan(intent=AgentIntent.GENERAL_CHAT, confidence=1.0, tools=list(self.tools), reasoning=f"{self.name()} owns this capability.", parameters={"user_message": request.user_message, "meeting_id": request.meeting_id})

    def execute(self, request: AgentRequest) -> AgentResult:
        started = perf_counter()
        plan = self.plan(request)
        tool_context = ToolContext(current_user=request.user_id, active_meeting=request.meeting_id, conversation_id=request.conversation_id)
        working = self.context.conversation_store.get_working_memory(request.conversation_id or f"user:{request.user_id}")
        executions, _ = self.context.reasoning_engine.execute(plan, tool_context, working_memory=working)
        self.context.metrics.agent_invocations += 1
        self.context.metrics.tool_usage += len(executions)
        self.context.metrics.execution_time_ms += (perf_counter() - started) * 1000
        failed = any(item.status != "completed" for item in executions)
        self.context.metrics.failures += int(failed)
        self.context.metrics.successes += int(not failed)
        return AgentResult(self.name(), str(executions[-1].output) if executions else "No tools required.", executions, failed)

    def reflect(self, result: AgentResult) -> str:
        return "completed" if not result.failed else "requires follow-up"

    def receive_message(self, message: AgentMessage) -> None:
        if message.receiver in {None, self.name()}:
            self.inbox.append(message)
