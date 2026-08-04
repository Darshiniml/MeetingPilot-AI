"""Approval queue for irreversible event-driven proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PendingApprovalTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    priority: str = "normal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"
    approved_by: int | None = None
    approved_at: datetime | None = None

    # Compatibility aliases for the original Milestone 5 adapter API.
    @property
    def task_id(self) -> str: return self.id
    @property
    def proposed_action(self) -> str: return self.action
    @property
    def required_tool(self) -> str: return self.tool
    @property
    def approval_status(self) -> str: return self.status


class PendingTaskQueue:
    def __init__(self) -> None:
        self._tasks: dict[str, PendingApprovalTask] = {}
        self._lock = RLock()

    def create(self, task: PendingApprovalTask) -> PendingApprovalTask:
        with self._lock:
            self._tasks[task.id] = task
        return task

    def add(self, task: PendingApprovalTask) -> PendingApprovalTask:
        return self.create(task)

    def approve(self, task_id: str, approved_by: int) -> PendingApprovalTask:
        return self._update(task_id, status="approved", approved_by=approved_by, approved_at=datetime.now(timezone.utc))

    def reject(self, task_id: str, approved_by: int | None = None) -> PendingApprovalTask:
        return self._update(task_id, status="rejected", approved_by=approved_by, approved_at=datetime.now(timezone.utc))

    def _update(self, task_id: str, **changes: Any) -> PendingApprovalTask:
        with self._lock:
            task = self._tasks[task_id].model_copy(update=changes)
            self._tasks[task_id] = task
        return task

    def list(self, status: str | None = None) -> list[PendingApprovalTask]:
        with self._lock:
            tasks = list(self._tasks.values())
        return [task for task in tasks if status is None or task.status == status]
