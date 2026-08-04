from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ApprovalItem(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str
    action_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED, EXECUTED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ApprovalEngine:
    """Manages the persistent, thread-safe queue of user actions awaiting permission approvals."""
    
    def __init__(self) -> None:
        self._queue: dict[str, ApprovalItem] = {}
        self._lock = RLock()

    def add_to_queue(self, decision_id: str, action_name: str, parameters: dict[str, Any]) -> ApprovalItem:
        with self._lock:
            item = ApprovalItem(
                decision_id=decision_id,
                action_name=action_name,
                parameters=parameters
            )
            self._queue[item.approval_id] = item
            logger.info("[ApprovalEngine] Queued action '%s' for user approval: Token %s", action_name, item.approval_id)
            return item

    def approve_action(self, approval_id: str) -> ApprovalItem | None:
        with self._lock:
            item = self._queue.get(approval_id)
            if item and item.status == "PENDING":
                item.status = "APPROVED"
                item.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info("[ApprovalEngine] Action approved by user: Token %s", approval_id)
                return item
            return None

    def reject_action(self, approval_id: str) -> bool:
        with self._lock:
            item = self._queue.get(approval_id)
            if item and item.status == "PENDING":
                item.status = "REJECTED"
                item.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info("[ApprovalEngine] Action rejected by user: Token %s", approval_id)
                return True
            return False

    def mark_executed(self, approval_id: str) -> None:
        with self._lock:
            item = self._queue.get(approval_id)
            if item:
                item.status = "EXECUTED"
                item.updated_at = datetime.now(timezone.utc).isoformat()

    def expire_old_actions(self, age_seconds: float = 3600.0) -> None:
        """Scan registry to transition stale entries into EXPIRED state."""
        now = datetime.now(timezone.utc)
        with self._lock:
            for item in self._queue.values():
                if item.status == "PENDING":
                    created = datetime.fromisoformat(item.created_at)
                    elapsed = (now - created).total_seconds()
                    if elapsed >= age_seconds:
                        item.status = "EXPIRED"
                        item.updated_at = now.isoformat()
                        logger.info("[ApprovalEngine] Approval request expired: %s", item.approval_id)

    def get_pending_approvals(self) -> list[ApprovalItem]:
        with self._lock:
            return [item for item in self._queue.values() if item.status == "PENDING"]

    def get_history(self) -> list[ApprovalItem]:
        with self._lock:
            return list(self._queue.values())
