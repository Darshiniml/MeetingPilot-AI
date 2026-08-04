"""Validates workflow graphs, checks for cycles, and ensures operation safety."""

import logging
from app.workflows.workflow_models import Workflow, WorkflowStep
from app.workflows.workflow_state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """Validates structural and safety properties of workflow DAGs."""

    def validate(self, workflow: Workflow) -> bool:
        """Run structural constraints and safety checks. Sets status to VALIDATED or FAILED."""
        WorkflowStateMachine.transition(workflow, "VALIDATING", reason="Starting structural validation checks")
        
        # 1. Verify we have steps
        if not workflow.steps:
            WorkflowStateMachine.transition(workflow, "FAILED", reason="Workflow has no steps configured")
            return False

        # 2. Check for missing dependencies or cycle loops
        if self._has_cycles_or_missing_dependencies(workflow.steps):
            WorkflowStateMachine.transition(workflow, "FAILED", reason="Structural dependency validation failed (cycle or missing dependency)")
            return False

        # 3. Check safety properties (e.g. destructive actions must have approval_required)
        for step in workflow.steps:
            WorkflowStateMachine.transition(step, "VALIDATING", reason="Validating step safety")
            
            # Destructive tools or parameters check
            is_destructive = False
            tool_name = step.tool.lower()
            if "delete" in tool_name or "remove" in tool_name or "wipe" in tool_name:
                is_destructive = True
            
            for key, val in step.parameters.items():
                if isinstance(val, str) and any(w in val.lower() for w in ("delete", "remove", "wipe")):
                    is_destructive = True
            
            if is_destructive and not step.approval_required:
                logger.warning("Step %s (%s) is destructive but not marked approval_required!", step.step_id, step.name)
                WorkflowStateMachine.transition(step, "FAILED", reason="Destructive action lacks approval requirement")
                WorkflowStateMachine.transition(workflow, "FAILED", reason=f"Safety check failed on step '{step.name}'")
                return False

            # Timeout sanity check
            if step.timeout is not None and step.timeout <= 0:
                WorkflowStateMachine.transition(step, "FAILED", reason="Timeout value must be greater than zero")
                WorkflowStateMachine.transition(workflow, "FAILED", reason=f"Invalid timeout in step '{step.name}'")
                return False
                
            WorkflowStateMachine.transition(step, "VALIDATED", reason="Safety checks passed")

        WorkflowStateMachine.transition(workflow, "VALIDATED", reason="All validation passes succeeded")
        return True

    def _has_cycles_or_missing_dependencies(self, steps: list[WorkflowStep]) -> bool:
        """Use DFS topological check to find cycle loops and verify dependencies exist."""
        adj = {step.step_id: step.depends_on for step in steps}
        visited = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(u: str) -> bool:
            visited[u] = 1
            for v in adj.get(u, []):
                # Missing dependency check
                if v not in adj:
                    logger.error("Step %s refers to non-existent step dependency: %s", u, v)
                    return True
                # Cycle check
                if visited.get(v, 0) == 1:
                    logger.error("Cyclic dependency loop detected: %s -> %s", u, v)
                    return True
                if visited.get(v, 0) == 0:
                    if dfs(v):
                        return True
            visited[u] = 2
            return False

        for step in steps:
            if visited.get(step.step_id, 0) == 0:
                if dfs(step.step_id):
                    return True
        return False
