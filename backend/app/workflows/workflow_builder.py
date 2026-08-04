"""Translates raw system events and Copilot alerts into executable workflows."""

import logging
from typing import Any
from app.workflows.workflow_models import Workflow, WorkflowStep
from app.workflows.workflow_registry import get_workflow_registry

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """Factory builder assembling executable Workflow graphs from events/insights."""

    def build_from_event(self, event_type: str, payload: dict[str, Any]) -> Workflow | None:
        """Map EventBus triggers to versioned workflow instances."""
        registry = get_workflow_registry()
        template_id = None
        
        # Map event names
        if event_type == "meeting_stopped":
            template_id = "meeting_finished"
        elif event_type == "meeting_started":
            template_id = "meeting_scheduled"

        if not template_id:
            return None

        template = registry.get(template_id)
        if not template or not template.enabled:
            return None

        # Build clean step copies
        step_copies = [self._copy_step(s) for s in template.steps]
        # Resolve positional DAG dependencies using copies' unique IDs
        self._map_step_dependency_uuids(step_copies, template.steps)

        # Inject context payload parameters
        for step in step_copies:
            step.parameters = {**step.parameters, **payload}

        workflow = Workflow(
            name=template.name,
            version=template.version,
            trigger_event=event_type,
            steps=step_copies,
            metadata={"payload": payload}
        )
        logger.info("Assembled workflow '%s' from event %s", workflow.name, event_type)
        return workflow

    def build_from_insight(self, insight_type: str, payload: dict[str, Any]) -> Workflow | None:
        """Map Copilot recommendations and semantic alerts to workflow draft templates."""
        registry = get_workflow_registry()
        template_id = None

        if insight_type == "decision":
            template_id = "decision_detected"
        elif insight_type == "deadline":
            template_id = "deadline_detected"
        elif insight_type == "commitment":
            template_id = "commitment_detected"
        elif insight_type == "risk":
            # Map risk to Customer Escalation template
            template_id = "customer_escalation"

        if not template_id:
            return None

        template = registry.get(template_id)
        if not template or not template.enabled:
            return None

        # Build step copies
        step_copies = [self._copy_step(s) for s in template.steps]
        self._map_step_dependency_uuids(step_copies, template.steps)

        # Inject context parameters
        for step in step_copies:
            step.parameters = {**step.parameters, **payload}

        workflow = Workflow(
            name=template.name,
            version=template.version,
            trigger_event=f"insight_{insight_type}",
            steps=step_copies,
            metadata={"insight_payload": payload}
        )
        logger.info("Assembled draft workflow '%s' from copilot insight: %s", workflow.name, insight_type)
        return workflow

    def _copy_step(self, step: WorkflowStep) -> WorkflowStep:
        """Create a new step copy keeping config details but generating fresh IDs."""
        return WorkflowStep(
            name=step.name,
            tool=step.tool,
            parameters=step.parameters.copy(),
            approval_required=step.approval_required,
            parallel_execution=step.parallel_execution,
            optional=step.optional,
            timeout=step.timeout,
            compensating_action=step.compensating_action.copy() if step.compensating_action else None,
            max_retries=step.max_retries
        )

    def _map_step_dependency_uuids(self, copies: list[WorkflowStep], originals: list[WorkflowStep]) -> None:
        """Remap positional dependencies using the new generated UUIDs."""
        # Map original step ID -> copied step ID
        mapping = {}
        for orig, copy in zip(originals, copies):
            mapping[orig.step_id] = copy.step_id

        # Update depends_on list in copies
        for copy, orig in zip(copies, originals):
            new_deps = []
            for dep in orig.depends_on:
                if dep in mapping:
                    new_deps.append(mapping[dep])
            copy.depends_on = new_deps
