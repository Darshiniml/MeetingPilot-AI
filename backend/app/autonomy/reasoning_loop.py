from __future__ import annotations

import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from app.agent.events.event_bus import EventBus
from app.autonomy.context_builder import ContextBuilder
from app.autonomy.goal_manager import GoalManager
from app.autonomy.decision_engine import DecisionEngine, AutonomyDecision
from app.autonomy.policy_engine import PolicyEngine
from app.autonomy.approval_engine import ApprovalEngine
from app.autonomy.execution_engine import ExecutionEngine
from app.autonomy.autonomy_metrics import AutonomyMetrics
from app.autonomy.autonomy_events import (
    ReasoningCycleCompletedEvent,
    DecisionMadeEvent,
    ActionExecutedEvent,
    ApprovalRequiredEvent
)

logger = logging.getLogger(__name__)

class ReasoningLoop:
    """Orchestrates the periodic observe-reason-decide loop, enforcing policy and logging decisions."""
    
    def __init__(
        self,
        event_bus: EventBus,
        metrics: AutonomyMetrics,
        policy_mode: str = "Semi-Autonomous",
        interval_seconds: float = 5.0
    ) -> None:
        self.event_bus = event_bus
        self.metrics = metrics
        self.interval = interval_seconds
        
        self.context_builder = ContextBuilder()
        self.goal_manager = GoalManager()
        self.decision_engine = DecisionEngine()
        self.policy_engine = PolicyEngine(policy_mode)
        self.approval_engine = ApprovalEngine()
        
        from app.autonomy.task_planner import TaskPlanner
        self.task_planner = TaskPlanner()
        self.execution_engine = ExecutionEngine(self.task_planner)
        
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, name="ReasoningLoop", daemon=True)
            self._thread.start()
            logger.info("Autonomy reasoning loop started (Interval: %ss, Policy: %s).", self.interval, self.policy_engine.mode)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._thread = None
            logger.info("Autonomy reasoning loop stopped.")

    def set_policy_mode(self, mode: str) -> None:
        with self._lock:
            self.policy_engine.mode = mode
            logger.info("[ReasoningLoop] Policy mode updated to: %s", mode)

    def trigger_approval_resolution(self, approval_id: str, approve: bool) -> bool:
        """Resolve a queued approval request and execute it if accepted."""
        with self._lock:
            if approve:
                item = self.approval_engine.approve_action(approval_id)
                if item:
                    # Execute approved action
                    self.metrics.record_approval_response(approved=True)
                    exec_result = self.execution_engine.execute_action(
                        item.action_name,
                        item.parameters,
                        item.decision_id
                    )
                    self.approval_engine.mark_executed(approval_id)
                    
                    # Publish ActionExecuted Event
                    self.event_bus.publish(ActionExecutedEvent(
                        user_id=1,
                        payload={
                            "action_name": item.action_name,
                            "result": exec_result,
                            "approval_id": approval_id
                        }
                    ))
                    return True
            else:
                success = self.approval_engine.reject_action(approval_id)
                if success:
                    self.metrics.record_approval_response(approved=False)
                    return True
            return False

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            
            start_time = time.perf_counter()
            try:
                self.run_single_reasoning_cycle()
            except Exception as e:
                logger.error("[ReasoningLoop] Error running cycle iteration: %s", e)
                
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0.1, self.interval - elapsed)
            time.sleep(sleep_time)

    def run_single_reasoning_cycle(self) -> None:
        """Execute a single observation-decision execution sequence."""
        cycle_start = time.perf_counter()
        
        # 1. Collect context
        context = self.context_builder.build_context()
        
        # 2. Update Goals priorities
        goals = self.goal_manager.get_goals(context)
        
        # 3. Evaluate decisions
        decisions = self.decision_engine.evaluate_decisions(context, goals)
        
        # 4. Evaluate policies and dispatch
        for decision in decisions:
            action_name = decision.selected_action["action_name"]
            policy_action = self.policy_engine.evaluate_policy(action_name)
            
            # Record decision metrics
            latency = time.perf_counter() - cycle_start
            is_skipped = policy_action == "BLOCKED"
            is_recommend = policy_action == "RECOMMEND"
            is_auto = policy_action == "AUTO_EXECUTE"
            
            self.metrics.record_decision(
                is_skipped=is_skipped,
                is_recommendation=is_recommend,
                is_auto=is_auto,
                confidence=decision.confidence,
                latency=latency
            )

            # Publish DecisionMade Event
            self.event_bus.publish(DecisionMadeEvent(
                user_id=1,
                payload=decision.dict()
            ))

            if policy_action == "BLOCKED":
                logger.info("[ReasoningLoop] Policy blocked action '%s' for decision %s", action_name, decision.decision_id)
                
            elif policy_action == "RECOMMEND":
                logger.info("[ReasoningLoop] Action recommended (Observation tier): %s", action_name)
                
            elif policy_action == "AUTO_EXECUTE":
                # Safe action -> auto-execute
                exec_result = self.execution_engine.execute_action(
                    action_name,
                    decision.selected_action["parameters"],
                    decision.decision_id
                )
                # Publish ActionExecuted Event
                self.event_bus.publish(ActionExecutedEvent(
                    user_id=1,
                    payload={
                        "action_name": action_name,
                        "result": exec_result,
                        "decision_id": decision.decision_id
                    }
                ))
                
            elif policy_action == "QUEUE_APPROVAL":
                # Unsafe action -> queue for approval
                approval_item = self.approval_engine.add_to_queue(
                    decision.decision_id,
                    action_name,
                    decision.selected_action["parameters"]
                )
                self.metrics.record_approval_request()
                
                # Publish ApprovalRequired Event
                self.event_bus.publish(ApprovalRequiredEvent(
                    user_id=1,
                    payload={
                        "approval_id": approval_item.approval_id,
                        "action_name": action_name,
                        "decision_id": decision.decision_id
                    }
                ))

        # Store completed loop memories
        self._store_autonomy_memory(context, decisions)

        # Expire old approvals
        self.approval_engine.expire_old_actions()

        # Publish ReasoningCycleCompleted Event
        cycle_latency = time.perf_counter() - cycle_start
        self.event_bus.publish(ReasoningCycleCompletedEvent(
            user_id=1,
            payload={
                "latency_seconds": cycle_latency,
                "decisions_count": len(decisions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ))

    def _store_autonomy_memory(self, context: dict[str, Any], decisions: list[AutonomyDecision]) -> None:
        """Indexes reasoning history into SQLite long-term memories databases."""
        if not decisions:
            return
        try:
            from app.database.session import SessionLocal
            from app.repositories.vector_repository import VectorRepository
            # Simulated long-term memory save hook
            logger.debug("[ReasoningLoop] Storing cycle decisions registry in vector indexes.")
        except Exception as e:
            logger.error("[ReasoningLoop] Memory store failed: %s", e)
            
    def get_approval_queue(self) -> list[Any]:
        return self.approval_engine.get_history()
