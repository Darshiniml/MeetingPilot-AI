"""Long-Term Semantic Memory Package with Dynamic Hooks."""

import logging
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# Request-scoped transaction context variables
current_user_id = ContextVar("current_user_id", default=1)
current_meeting_id = ContextVar("current_meeting_id", default=None)
current_conversation_id = ContextVar("current_conversation_id", default=None)


def initialize_memory_hooks() -> None:
    """Register runtime hooks and monkeypatches to dynamically inject memory capabilities."""
    logger.info("Initializing persistent long-term memory integration hooks...")

    # 1. EventBus hook for auto-indexing
    try:
        from app.agent.events.event_bus import EventBus
        from app.memory.memory_manager import get_memory_manager
        
        _original_publish = EventBus.publish
        def wrapped_publish(self, event: Any) -> None:
            _original_publish(self, event)
            try:
                # Update ContextVars from published event metadata if not set
                token_u = None
                token_m = None
                if event.user_id:
                    token_u = current_user_id.set(event.user_id)
                if event.meeting_id:
                    token_m = current_meeting_id.set(event.meeting_id)
                
                mgr = get_memory_manager()
                mgr.indexer.handle_event(event)
                
                if token_u:
                    current_user_id.reset(token_u)
                if token_m:
                    current_meeting_id.reset(token_m)
            except Exception as ex:
                logger.exception("Memory indexer failed to handle event: %s", ex)
        EventBus.publish = wrapped_publish
        logger.info(" -> EventBus.publish hooked successfully.")
    except Exception as e:
        logger.error("Could not hook EventBus.publish: %s", e)

    # 2. Planner hook to inject long-term memories
    try:
        from app.agent.planner import Planner
        from app.agent.models import ExecutionPlan
        
        _original_plan = Planner.plan
        def wrapped_plan(self, user_message: str, memory_context: dict | None = None) -> ExecutionPlan:
            if memory_context is None:
                memory_context = {}
            
            user_id = current_user_id.get(1)
            meeting_id = current_meeting_id.get(None)
            conv_id = current_conversation_id.get(None)

            try:
                mgr = get_memory_manager()
                memories = mgr.retrieve_memories(
                    user_id=user_id,
                    query=user_message,
                    limit=10,
                    current_meeting_id=meeting_id,
                    current_conversation_id=conv_id
                )
                memory_context["long_term_memory"] = [
                    {
                        "type": m["memory_type"],
                        "title": m["title"],
                        "content": m["content"],
                        "importance": m["importance_score"]
                    }
                    for m in memories
                ]
                logger.info("Injected %d long-term memories into Planner context", len(memories))
            except Exception as ex:
                logger.exception("Failed to retrieve long-term memories for planner: %s", ex)

            return _original_plan(self, user_message, memory_context)
        Planner.plan = wrapped_plan
        logger.info(" -> Planner.plan hooked successfully.")
    except Exception as e:
        logger.error("Could not hook Planner.plan: %s", e)

    # 3. SupervisorAgent hook to load memory context before delegation
    try:
        from app.agents.supervisor_agent import SupervisorAgent
        from app.agent.models import AgentRequest, AgentResponse
        
        _original_supervisor_handle = SupervisorAgent.handle
        def wrapped_supervisor_handle(self, request: AgentRequest) -> AgentResponse:
            token_u = current_user_id.set(request.user_id)
            token_m = current_meeting_id.set(request.meeting_id)
            token_c = current_conversation_id.set(request.conversation_id)
            
            try:
                # Pre-fetch memory context and load into shared working memory
                mgr = get_memory_manager()
                memories = mgr.retrieve_memories(
                    user_id=request.user_id,
                    query=request.user_message,
                    limit=10,
                    current_meeting_id=request.meeting_id,
                    current_conversation_id=request.conversation_id
                )
                
                working_memory = self.context.conversation_store.get_working_memory(
                    request.conversation_id or f"user:{request.user_id}"
                )
                working_memory.tool_outputs["long_term_memory"] = [
                    {"title": m["title"], "content": m["content"], "type": m["memory_type"], "score": m["score"]}
                    for m in memories
                ]
            except Exception as ex:
                logger.exception("Supervisor memory integration fetch failed: %s", ex)
            
            try:
                return _original_supervisor_handle(self, request)
            finally:
                current_user_id.reset(token_u)
                current_meeting_id.reset(token_m)
                current_conversation_id.reset(token_c)
        SupervisorAgent.handle = wrapped_supervisor_handle
        logger.info(" -> SupervisorAgent.handle hooked successfully.")
    except Exception as e:
        logger.error("Could not hook SupervisorAgent.handle: %s", e)

    # 4. AgentController hook (fallback handler)
    try:
        from app.agent.agent_controller import AgentController
        from app.agent.models import AgentRequest, AgentResponse
        
        _original_controller_handle = AgentController.handle
        def wrapped_controller_handle(self, request: AgentRequest) -> AgentResponse:
            token_u = current_user_id.set(request.user_id)
            token_m = current_meeting_id.set(request.meeting_id)
            token_c = current_conversation_id.set(request.conversation_id)
            try:
                return _original_controller_handle(self, request)
            finally:
                current_user_id.reset(token_u)
                current_meeting_id.reset(token_m)
                current_conversation_id.reset(token_c)
        AgentController.handle = wrapped_controller_handle
        logger.info(" -> AgentController.handle hooked successfully.")
    except Exception as e:
        logger.error("Could not hook AgentController.handle: %s", e)

    # 5. Reflection hook to index successful/failed executions
    try:
        from app.agent.reflection import ReflectionEngine
        from app.agent.memory_models import ReflectionRecord
        from app.agent.models import ExecutionPlan, ToolExecution
        
        _original_reflect = ReflectionEngine.reflect
        def wrapped_reflect(self, plan: ExecutionPlan, executions: list[ToolExecution]) -> ReflectionRecord:
            record = _original_reflect(self, plan, executions)
            
            try:
                user_id = current_user_id.get(1)
                meeting_id = current_meeting_id.get(None)
                conv_id = current_conversation_id.get(None)
                
                tool_list = plan.tools or []
                failures = [item.tool_name for item in executions if item.status == "failed"]
                successes = [item.tool_name for item in executions if item.status == "completed"]
                
                content = (
                    f"Plan intent: {plan.intent.value if plan.intent else 'UNKNOWN'}\n"
                    f"Intended tools: {tool_list}\n"
                    f"Successful tools: {successes}\n"
                    f"Failed tools: {failures}\n"
                    f"Reflection feedback: {record.reflection}\n"
                    f"Recommendations: {record.future_recommendations}"
                )
                
                mgr = get_memory_manager()
                mgr.add_custom_memory(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    conversation_id=conv_id,
                    memory_type="ReflectionMemory",
                    title="Agent reasoning and tool execution reflection",
                    content=content,
                    metadata={
                        "confidence_adjustment": record.confidence_adjustment,
                        "future_recommendations": record.future_recommendations,
                        "success": len(failures) == 0
                    }
                )
            except Exception as ex:
                logger.exception("Reflection indexer failed: %s", ex)
                
            return record
        ReflectionEngine.reflect = wrapped_reflect
        logger.info(" -> ReflectionEngine.reflect hooked successfully.")
    except Exception as e:
        logger.error("Could not hook ReflectionEngine.reflect: %s", e)


# Run hooks immediately on package import
initialize_memory_hooks()
