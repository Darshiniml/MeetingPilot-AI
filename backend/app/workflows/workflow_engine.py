"""Central orchestrator managing workflow validation, execution tasks, and recovery replays."""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any

from app.workflows.workflow_models import Workflow
from app.workflows.workflow_builder import WorkflowBuilder
from app.workflows.workflow_validator import WorkflowValidator
from app.workflows.workflow_executor import WorkflowExecutor
from app.workflows.workflow_metrics import get_workflow_metrics
from app.workflows.workflow_state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)

STATE_FILE = r"C:\Users\Varshini\.gemini\antigravity\brain\72befde9-cc90-4e79-ab5c-4f6fbf223ff1\workflows_state.json"


class WorkflowEngine:
    """Manages active automation workflows, recovery, and persistence lifecycle."""

    def __init__(self) -> None:
        self.builder = WorkflowBuilder()
        self.validator = WorkflowValidator()
        self.executor = WorkflowExecutor()
        self.metrics = get_workflow_metrics()
        self._workflows: dict[str, Workflow] = {}
        
        # Load persisted workflows and trigger replay recovery
        self._load_state_from_disk()
        self.event_replay_recovery()

    def create_workflow_from_event(self, event_type: str, payload: dict[str, Any]) -> Workflow | None:
        """Construct, validate, and execute a workflow triggered by EventBus events."""
        workflow = self.builder.build_from_event(event_type, payload)
        if not workflow:
            return None

        self._workflows[workflow.workflow_id] = workflow
        self.metrics.record_workflow_created()
        self._save_state_to_disk()

        # Run validation
        if self.validator.validate(workflow):
            self.start_workflow_task(workflow)
        else:
            self.metrics.record_workflow_failed()
            self._save_state_to_disk()

        return workflow

    def create_workflow_from_insight(self, insight_type: str, payload: dict[str, Any]) -> Workflow | None:
        """Construct, validate, and queue a workflow triggered by Copilot insights."""
        workflow = self.builder.build_from_insight(insight_type, payload)
        if not workflow:
            return None

        self._workflows[workflow.workflow_id] = workflow
        self.metrics.record_workflow_created()
        self._save_state_to_disk()

        # Run validation
        if self.validator.validate(workflow):
            self.start_workflow_task(workflow)
        else:
            self.metrics.record_workflow_failed()
            self._save_state_to_disk()

        return workflow

    def start_workflow_task(self, workflow: Workflow) -> None:
        """Launch background async execution loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_execution_loop(workflow))
        except RuntimeError:
            # Fallback if no running loop in current thread
            asyncio.run(self._run_execution_loop(workflow))

    async def _run_execution_loop(self, workflow: Workflow) -> None:
        """Execute step loop and record results in long term memories."""
        start_time = datetime.now(timezone.utc)
        
        success = await self.executor.execute(workflow)
        self._save_state_to_disk()
        
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        if success:
            self.metrics.record_workflow_completed(duration_ms)
            self._save_history_memory(workflow, "Workflow Completed successfully")
        else:
            self.metrics.record_workflow_failed()
            self._save_history_memory(workflow, f"Workflow Failed: {workflow.status}")

    def resume_workflow(
        self,
        workflow_id: str,
        step_id: str,
        approval_status: str = "approved",
        parameter_overrides: dict[str, Any] | None = None
    ) -> bool:
        """Resume a workflow currently waiting on approval."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error("Could not resume: workflow not found: %s", workflow_id)
            return False

        # Find target step
        step = next((s for s in workflow.steps if s.step_id == step_id), None)
        if not step:
            logger.error("Could not resume: step %s not found in workflow %s", step_id, workflow_id)
            return False

        # Handle override options
        if approval_status == "approved" or approval_status == "modified":
            WorkflowStateMachine.transition(step, "APPROVED", reason=f"User marked: {approval_status}")
            if parameter_overrides:
                step.parameters = {**step.parameters, **parameter_overrides}
            # Set workflow status back to validated to resume execution loop
            WorkflowStateMachine.transition(workflow, "VALIDATED", reason="Resuming execution loop")
            self._save_state_to_disk()
            
            self.start_workflow_task(workflow)
            return True
        elif approval_status == "rejected":
            WorkflowStateMachine.transition(step, "FAILED", reason="User rejected step execution")
            WorkflowStateMachine.transition(workflow, "FAILED", reason="Step execution rejected by user")
            self._save_state_to_disk()
            return True

        return False

    def cancel_workflow(self, workflow_id: str) -> None:
        """Transition workflow and all non-completed steps to CANCELLED state."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return
        WorkflowStateMachine.transition(workflow, "CANCELLED", reason="User manually cancelled execution")
        for step in workflow.steps:
            if step.status not in ("COMPLETED", "FAILED"):
                WorkflowStateMachine.transition(step, "CANCELLED", reason="Workflow cancelled")
        self._save_state_to_disk()

    def event_replay_recovery(self) -> None:
        """Scan active states list and resume unfinished tasks after application restart."""
        recovered = 0
        for workflow in list(self._workflows.values()):
            if workflow.status in ("RUNNING", "QUEUED", "VALIDATING"):
                logger.info("EventReplay: Recovering unfinished workflow %s (%s)", workflow.workflow_id, workflow.name)
                # Re-validate and run
                WorkflowStateMachine.transition(workflow, "VALIDATED", reason="Recovered during replay")
                self.start_workflow_task(workflow)
                recovered += 1
        if recovered > 0:
            logger.info("EventReplay recovery check complete: replayed %d workflows", recovered)

    def _save_history_memory(self, workflow: Workflow, summary: str) -> None:
        """Persist workflow log summary as long term memory."""
        try:
            from app.memory.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            steps_info = [
                {"name": s.name, "tool": s.tool, "status": s.status, "error": s.error_message}
                for s in workflow.steps
            ]
            content = (
                f"Workflow: {workflow.name}\n"
                f"Status: {workflow.status}\n"
                f"Trigger: {workflow.trigger_event}\n"
                f"Summary: {summary}\n"
                f"Steps: {json.dumps(steps_info, indent=2)}"
            )
            mgr.add_custom_memory(
                user_id=1,
                memory_type="WorkflowMemory",
                title=f"Workflow Execution: {workflow.name}",
                content=content,
                metadata={
                    "workflow_id": workflow.workflow_id,
                    "status": workflow.status,
                    "trigger_event": workflow.trigger_event
                }
            )
        except Exception as e:
            logger.exception("Failed to write workflow history memory: %s", e)

    def _save_state_to_disk(self) -> None:
        """Serialize and dump workflow map to local workspace JSON file."""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            data = [w.model_dump(mode="json") for w in self._workflows.values()]
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.exception("Failed to save workflow state: %s", e)

    def _load_state_from_disk(self) -> None:
        """Load and deserialize workflow map from local workspace JSON file."""
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                w = Workflow(**item)
                self._workflows[w.workflow_id] = w
            logger.info("Loaded %d workflows from state file.", len(self._workflows))
        except Exception as e:
            logger.exception("Failed to load workflow state: %s", e)


# Global singleton instance
_workflow_engine = None


def get_workflow_engine() -> WorkflowEngine:
    """Return the shared WorkflowEngine singleton."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
