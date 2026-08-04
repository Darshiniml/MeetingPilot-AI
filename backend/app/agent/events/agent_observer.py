"""Autonomous observer that turns permitted system events into agent work."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import perf_counter

from ..context import AgentContext
from ..conversation_store import ConversationStore
from ..memory_models import ConversationInteraction
from ..models import AgentRequest, ExecutionPlan, ToolExecution
from ..planner import Planner
from ..reasoning_engine import ReasoningEngine
from ..reflection import ReflectionEngine
from .autonomous_policy import AutonomousPolicy, PolicyDecision
from .event_models import BaseAgentEvent
from .metrics import AgentEventMetrics
from .pending_tasks import PendingApprovalTask, PendingTaskQueue

logger = logging.getLogger(__name__)


@dataclass
class AutonomousEventResult:
    event_id: str
    policy: PolicyDecision
    plan: ExecutionPlan | None = None
    executions: list[ToolExecution] = field(default_factory=list)
    pending_tasks: list[PendingApprovalTask] = field(default_factory=list)


class AgentObserver:
    """Evaluates events, invokes planning, and protects approval-gated actions."""

    def __init__(self, planner: Planner, reasoning_engine: ReasoningEngine, policy: AutonomousPolicy | None = None, pending_tasks: PendingTaskQueue | None = None, conversation_store: ConversationStore | None = None, reflection_engine: ReflectionEngine | None = None, metrics: AgentEventMetrics | None = None) -> None:
        self._planner = planner
        self._reasoning_engine = reasoning_engine
        self._policy = policy or AutonomousPolicy()
        self._pending_tasks = pending_tasks or PendingTaskQueue()
        self._conversation_store = conversation_store or ConversationStore()
        self._reflection_engine = reflection_engine or ReflectionEngine()
        self.metrics = metrics or AgentEventMetrics()
        self._event_bus = None

    @property
    def pending_tasks(self) -> PendingTaskQueue:
        return self._pending_tasks

    def attach_event_bus(self, event_bus) -> None:
        """Attach the bus only when wired by the additive event dispatcher."""
        self._event_bus = event_bus

    def on_event(self, event: BaseAgentEvent) -> AutonomousEventResult:
        started_at = perf_counter()
        self.metrics.increment("events_processed")
        decision = self._policy.evaluate(event)
        logger.info("Autonomous policy: event=%s react=%s", event.event_type.value, decision.should_react)
        result = AutonomousEventResult(event_id=event.event_id, policy=decision)
        if not decision.should_react:
            return result

        conversation_id = f"event-user:{event.user_id}"
        previous = self._conversation_store.retrieve(conversation_id, decision.message)
        working_memory = self._conversation_store.get_working_memory(conversation_id)
        self.metrics.increment("memory_hits" if previous else "memory_misses")
        request = AgentRequest(user_message=decision.message, user_id=event.user_id, meeting_id=event.meeting_id, conversation_id=conversation_id)
        self.metrics.increment("planner_calls")
        plan = self._planner.plan(request.user_message, memory_context={"event": event.model_dump(mode="json"), "recent_conversation": [item.model_dump(mode="json") for item in previous], "working_memory": working_memory.context(), "recommendation": decision.recommendation})
        result.plan = plan
        safe_tools = []
        for tool_name in plan.tools:
            if self._policy.requires_approval(tool_name):
                task = self._pending_tasks.create(PendingApprovalTask(action=f"Autonomous event action: {tool_name}", tool=tool_name, parameters=plan.parameters, reason=decision.recommendation or plan.reasoning))
                result.pending_tasks.append(task)
                self.metrics.increment("pending_approvals")
                logger.info("Pending approval created: task=%s tool=%s", task.task_id, tool_name)
            else:
                safe_tools.append(tool_name)
        if safe_tools:
            safe_plan = plan.model_copy(update={"tools": safe_tools})
            context = AgentContext(current_user=event.user_id, active_meeting=event.meeting_id, conversation_id=request.conversation_id, request_metadata={"event_id": event.event_id, "event_type": event.event_type.value})
            result.executions, _ = self._reasoning_engine.execute(safe_plan, context, working_memory=working_memory)
            self.metrics.increment("tool_executions", len(result.executions))
            if self._event_bus is not None and event.event_type.value != "summary_generated":
                for execution in result.executions:
                    if execution.tool_name == "summary" and execution.status == "completed":
                        from .event_models import SummaryGeneratedEvent
                        self._event_bus.publish(SummaryGeneratedEvent(user_id=event.user_id, meeting_id=event.meeting_id, payload={"summary": execution.output, "source_event_id": event.event_id}))
        reflection = self._reflection_engine.reflect(plan, result.executions)
        self._conversation_store.get_conversation(conversation_id).add(ConversationInteraction(user_message=request.user_message, planner_decision=plan.model_dump(mode="json"), tool_outputs={item.tool_name: item.output for item in result.executions}, agent_response=decision.recommendation, reflection=reflection))
        if decision.recommendation:
            self.metrics.increment("autonomous_recommendations")
        logger.info("Autonomous reflection: %s", reflection.reflection)
        logger.info("Autonomous event completed: event=%s duration_ms=%.2f", event.event_id, (perf_counter() - started_at) * 1000)
        return result
