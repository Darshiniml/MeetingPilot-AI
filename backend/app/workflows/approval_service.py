"""Extended approval service queue supporting delegate, postpone, and parameter overrides."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.agent.events.pending_tasks import PendingApprovalTask, PendingTaskQueue
from app.workflows.workflow_models import WorkflowApproval

logger = logging.getLogger(__name__)


class ApprovalService:
    """Orchestrates manual approval gates for workflow execution steps."""

    def __init__(self, task_queue: PendingTaskQueue | None = None) -> None:
        self._queue = task_queue or PendingTaskQueue()
        self._approvals: dict[str, WorkflowApproval] = {}

    def request_step_approval(
        self,
        workflow_id: str,
        step_id: str,
        tool: str,
        parameters: dict[str, Any],
        reason: str
    ) -> str:
        """Create and queue a PendingApprovalTask, returning the task/approval ID."""
        task = PendingApprovalTask(
            action=f"Execute workflow step: {tool}",
            tool=tool,
            parameters=parameters,
            reason=reason
        )
        self._queue.add(task)
        
        approval = WorkflowApproval(
            approval_id=task.id,
            workflow_id=workflow_id,
            step_id=step_id,
            status="pending",
            reason=reason
        )
        self._approvals[task.id] = approval
        
        logger.info("Queued approval request: approval_id=%s workflow=%s step=%s", task.id, workflow_id, step_id)
        return task.id

    def approve(self, approval_id: str, user_id: int) -> WorkflowApproval | None:
        """Set approval status to APPROVED."""
        self._queue.approve(approval_id, approved_by=user_id)
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "approved"
            logger.info("Step approved: approval_id=%s", approval_id)
        return approval

    def reject(self, approval_id: str, user_id: int) -> WorkflowApproval | None:
        """Set approval status to REJECTED."""
        self._queue.reject(approval_id, approved_by=user_id)
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "rejected"
            logger.info("Step rejected: approval_id=%s", approval_id)
        return approval

    def modify_parameters(self, approval_id: str, new_parameters: dict[str, Any]) -> WorkflowApproval | None:
        """Override step parameters and mark status as MODIFIED."""
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "modified"
            # Update parameters in queue task
            with self._queue._lock:
                if approval_id in self._queue._tasks:
                    self._queue._tasks[approval_id] = self._queue._tasks[approval_id].model_copy(
                        update={"parameters": new_parameters}
                    )
            logger.info("Step modified parameters: approval_id=%s params=%s", approval_id, new_parameters)
        return approval

    def delegate(self, approval_id: str, delegate_to: str) -> WorkflowApproval | None:
        """Reassign approval task to delegate_to."""
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "delegated"
            approval.delegate_to = delegate_to
            logger.info("Step delegated: approval_id=%s delegated_to=%s", approval_id, delegate_to)
        return approval

    def postpone(self, approval_id: str, until_time: datetime) -> WorkflowApproval | None:
        """Delay execution gate until until_time."""
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = "postponed"
            approval.postpone_until = until_time
            logger.info("Step postponed: approval_id=%s until=%s", approval_id, until_time.isoformat())
        return approval

    def get_approval(self, approval_id: str) -> WorkflowApproval | None:
        """Fetch approval record by ID."""
        return self._approvals.get(approval_id)


# Global singleton instance
_approval_service = None


def get_approval_service() -> ApprovalService:
    """Return the shared ApprovalService singleton."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service
