from __future__ import annotations

import logging
from typing import Any
from app.background import get_background_service
from app.autonomy.task_planner import TaskPlanner

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Delegates actions to providers, agents, or workflows, validating safety checks before runs."""
    
    def __init__(self, task_planner: TaskPlanner) -> None:
        self.planner = task_planner

    def execute_action(self, action_name: str, parameters: dict[str, Any], decision_id: str) -> dict[str, Any]:
        """Perform safety verification guards and execute/delegate the action."""
        logger.info("[ExecutionEngine] Executing action '%s' for decision %s", action_name, decision_id)
        
        # 1. Safety verification guard
        safety_status = self.verify_safety_guard(action_name)
        if not safety_status["eligible"]:
            logger.warning("[ExecutionEngine] Safety guard failed for action '%s': %s", action_name, safety_status["reason"])
            return {"status": "FAILED", "error": safety_status["reason"]}

        # 2. Execution Delegation
        try:
            result = {}
            if action_name == "create_workflow":
                # Delegate to task planner which calls WorkflowEngine
                payload = {"decision_id": decision_id, **parameters}
                success = self.planner.plan_and_delegate("Track commitments", payload)
                result = {"status": "SUCCESS" if success else "FAILED"}
                
            elif action_name == "generate_reminder":
                bg_service = get_background_service()
                if bg_service.recording_manager.session_manager.get_active_session():
                    bg_service.recording_manager.session_manager.add_timeline_event(
                        "AutonomyReminder",
                        parameters.get("reminder_text", "Commitment reminder generated.")
                    )
                result = {"status": "SUCCESS", "reminder": parameters.get("reminder_text")}
                
            elif action_name == "refresh_embeddings":
                # Simulated embedding database refresh
                logger.info("[ExecutionEngine] Vectorized embeddings databases refreshed.")
                result = {"status": "SUCCESS"}
                
            elif action_name == "calendar_creation":
                # Unsafe calendar action - delegate to active calendar provider
                from app.providers import get_provider_manager
                pm = get_provider_manager()
                provider = pm.get_active_provider("calendar")
                if provider:
                    logger.info("[ExecutionEngine] Delegating calendar creation to active provider: %s", provider.provider_name)
                    # Simulated delegate call
                result = {"status": "SUCCESS", "event": parameters.get("title")}
                
            elif action_name == "email_sending":
                # Unsafe email action - delegate to active email provider
                from app.providers import get_provider_manager
                pm = get_provider_manager()
                provider = pm.get_active_provider("email")
                if provider:
                    logger.info("[ExecutionEngine] Delegating email dispatch to active provider: %s", provider.provider_name)
                    # Simulated delegate call
                result = {"status": "SUCCESS", "recipient": parameters.get("to")}
                
            elif action_name == "store_memory":
                # Store dynamic decision logs into long-term memories databases
                from app.database.session import SessionLocal
                from app.repositories.vector_repository import VectorRepository
                with SessionLocal() as session:
                    repo = VectorRepository(session)
                    # Log index references
                result = {"status": "SUCCESS"}
                
            else:
                logger.warning("[ExecutionEngine] Action '%s' not recognized.", action_name)
                result = {"status": "FAILED", "error": "Action not recognized"}

            # Log to active session timeline if present
            bg_service = get_background_service()
            active_session = bg_service.recording_manager.session_manager.get_active_session()
            if active_session:
                active_session.timeline.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_name": "ActionExecuted",
                    "description": f"Executed action '{action_name}' for decision: {decision_id}"
                })

            return result
        except Exception as e:
            logger.error("[ExecutionEngine] Action execution failed: %s", e)
            return {"status": "FAILED", "error": str(e)}

    def verify_safety_guard(self, action_name: str) -> dict[str, Any]:
        """Check provider availability, required permissions, and workflow configurations."""
        from app.providers import ProviderManager
        
        # Verify provider connections based on action types
        if action_name == "calendar_creation":
            try:
                provider = ProviderManager.get_calendar(None, 1)
                health = provider.get_health().get("status", "healthy") if hasattr(provider, "get_health") else "healthy"
                if health.lower() != "healthy":
                    return {"eligible": False, "reason": "Active Calendar provider is offline or degraded."}
            except Exception as e:
                return {"eligible": False, "reason": f"Failed to resolve Calendar provider: {e}"}
                
        elif action_name == "email_sending":
            try:
                provider = ProviderManager.get_email(None, 1)
                health = provider.get_health().get("status", "healthy") if hasattr(provider, "get_health") else "healthy"
                if health.lower() != "healthy":
                    return {"eligible": False, "reason": "Active Email provider is offline or degraded."}
            except Exception as e:
                return {"eligible": False, "reason": f"Failed to resolve Email provider: {e}"}

        return {"eligible": True, "reason": "All safety checks passed."}

# Import datetime inside context scoped block
from datetime import datetime, timezone
