"""Orchestration entry point for the autonomous agent framework."""

from __future__ import annotations

import logging
from time import perf_counter
from .context import AgentContext
from .conversation_store import ConversationStore
from .memory_models import ConversationInteraction
from .models import AgentRequest, AgentResponse, ToolExecution
from .planner import Planner
from .reasoning_engine import ReasoningEngine
from .reflection import ReflectionEngine
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentController:
    """Builds context, plans execution, and invokes registered generic tools."""

    def __init__(self, planner: Planner | None = None, registry: ToolRegistry | None = None, reasoning_engine: ReasoningEngine | None = None, conversation_store: ConversationStore | None = None, reflection_engine: ReflectionEngine | None = None) -> None:
        self.planner = planner or Planner()
        self.registry = registry or ToolRegistry()
        self.reasoning_engine = reasoning_engine or ReasoningEngine(self.registry)
        self.conversation_store = conversation_store or ConversationStore()
        self.reflection_engine = reflection_engine or ReflectionEngine()

    def handle(self, request: AgentRequest) -> AgentResponse:
        """Process a request and always represent unavailable tools as a result."""
        started_at = perf_counter()
        context = self._build_context(request)
        conversation_id = request.conversation_id or f"user:{request.user_id}"
        memories = self.conversation_store.retrieve(conversation_id, request.user_message)
        working_memory = self.conversation_store.get_working_memory(conversation_id)
        planner_context = {
            "recent_conversation": [item.model_dump(mode="json") for item in memories],
            "working_memory": working_memory.context(),
            "current_meeting": request.meeting_id,
        }
        logger.info("Agent memory %s for conversation %s", "hit" if memories else "miss", conversation_id)
        plan = self.planner.plan(request.user_message, memory_context=planner_context)
        executions, _execution_context = self.reasoning_engine.execute(plan, context, working_memory=working_memory)

        answer = self._answer_for(plan.tools, executions)
        response = AgentResponse(
            answer=answer,
            execution_plan=plan,
            tool_executions=executions,
            total_execution_time=(perf_counter() - started_at) * 1000,
        )
        logger.info("Agent request completed in %.2f ms", response.total_execution_time)
        reflection = self.reflection_engine.reflect(plan, executions)
        logger.info("Agent reflection: %s", reflection.reflection)
        self.conversation_store.get_conversation(conversation_id).add(
            ConversationInteraction(
                user_message=request.user_message,
                planner_decision=plan.model_dump(mode="json"),
                tool_outputs={item.tool_name: item.output for item in executions},
                agent_response=response.answer,
                reflection=reflection,
            )
        )
        return response

    @staticmethod
    def _build_context(request: AgentRequest) -> AgentContext:
        return AgentContext(
            current_user=request.user_id,
            active_meeting=request.meeting_id,
            conversation_id=request.conversation_id,
            request_metadata={"user_message": request.user_message},
        )

    @staticmethod
    def _answer_for(tools: list[str], executions: list[ToolExecution]) -> str:
        if not tools:
            return "No specialized tool is required for this request."
        if any(execution.status == "missing" for execution in executions):
            return "Tool not yet registered"
        if any(execution.status == "failed" for execution in executions):
            return "A tool could not complete the request."
        return str(executions[-1].output) if executions else "Request completed."
