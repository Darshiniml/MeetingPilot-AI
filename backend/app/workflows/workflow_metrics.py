"""Tracks execution success ratios, latency logs, and manual approval rate stats."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """Metrics tracking registry compiling workflow execution metrics."""

    def __init__(self) -> None:
        self.workflow_count = 0
        self.completed_count = 0
        self.failed_count = 0
        self.retry_count = 0
        self.compensations_run = 0
        
        # Approvals trackers
        self.approvals_requested = 0
        self.approvals_approved = 0
        self.approvals_rejected = 0
        
        # Duration latencies
        self.total_duration_ms = 0.0
        self.duration_runs_count = 0

    def record_workflow_created(self) -> None:
        """Increment workflow creation count."""
        self.workflow_count += 1

    def record_workflow_completed(self, duration_ms: float) -> None:
        """Log a successful execution completed metric."""
        self.completed_count += 1
        if duration_ms > 0:
            self.total_duration_ms += duration_ms
            self.duration_runs_count += 1

    def record_workflow_failed(self) -> None:
        """Log a failed workflow completion event."""
        self.failed_count += 1

    def record_retry(self) -> None:
        """Log a step execution retry event."""
        self.retry_count += 1

    def record_compensation_run(self) -> None:
        """Log a compensating rollback trigger."""
        self.compensations_run += 1

    def record_approval_requested(self) -> None:
        """Log an approval queue request event."""
        self.approvals_requested += 1

    def record_approval_action(self, status: str) -> None:
        """Log manual approval responses."""
        if status == "approved":
            self.approvals_approved += 1
        elif status == "rejected":
            self.approvals_rejected += 1

    def get_stats(self) -> dict[str, Any]:
        """Compile and return current ratio performance summaries."""
        total_started = self.completed_count + self.failed_count
        completion_rate = (self.completed_count / total_started) if total_started > 0 else 0.0
        failure_rate = (self.failed_count / total_started) if total_started > 0 else 0.0
        
        total_approval_decisions = self.approvals_approved + self.approvals_rejected
        approval_rate = (self.approvals_approved / total_approval_decisions) if total_approval_decisions > 0 else 0.0

        avg_duration = (self.total_duration_ms / self.duration_runs_count) if self.duration_runs_count > 0 else 0.0

        return {
            "workflow_count": self.workflow_count,
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "approval_rate": approval_rate,
            "retry_count": self.retry_count,
            "compensations_run": self.compensations_run,
            "average_duration_ms": avg_duration
        }


# Global singleton instance
_workflow_metrics = None


def get_workflow_metrics() -> WorkflowMetrics:
    """Return the shared WorkflowMetrics singleton."""
    global _workflow_metrics
    if _workflow_metrics is None:
        _workflow_metrics = WorkflowMetrics()
    return _workflow_metrics
