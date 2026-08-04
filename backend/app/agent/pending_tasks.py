"""In-memory queue for agent proposals requiring user approval."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PendingApprovalTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    proposed_action: str
    required_tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    approval_status: str = "pending"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PendingTaskQueue:
    """Thread-safe process-local queue; persistence is intentionally out of scope."""

    def __init__(self) -> None:
        self._tasks: dict[str, PendingApprovalTask] = {}
        self._lock = RLock()

    def add(self, task: PendingApprovalTask) -> PendingApprovalTask:
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def list(self, status: str | None = None) -> list[PendingApprovalTask]:
        with self._lock:
            tasks = list(self._tasks.values())
        return [task for task in tasks if status is None or task.approval_status == status]

    def set_status(self, task_id: str, status: str) -> PendingApprovalTask:
        if status not in {"approved", "rejected"}:
            raise ValueError("Approval status must be approved or rejected.")
        with self._lock:
            task = self._tasks[task_id]
            updated = task.model_copy(update={"approval_status": status})
            self._tasks[task_id] = updated
        return updated
