"""Pydantic schemas and models for DAG-based autonomous workflows."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    """An individual operation step in a workflow execution graph."""

    step_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: str = "CREATED"  # StateMachine states
    approval_required: bool = False
    
    # DAG-based fields
    depends_on: list[str] = Field(default_factory=list)  # step_ids this step depends on
    parallel_execution: bool = False
    optional: bool = False
    timeout: float | None = None  # timeout in seconds
    
    # Recovery and Compensations
    compensating_action: dict[str, Any] | None = None  # action payload to undo this step
    error_message: str | None = None
    result: Any | None = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Timestamps
    started_at: datetime | None = None
    ended_at: datetime | None = None
    
    # Audit Trail
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowTemplate(BaseModel):
    """A versioned workflow design template."""

    template_id: str
    name: str
    version: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    steps: list[WorkflowStep]


class Workflow(BaseModel):
    """An active running instance of a workflow."""

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    version: str = "1.0.0"
    trigger_event: str | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    status: str = "CREATED"
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Scheduled execution
    schedule_type: str = "event_triggered"  # "run_now", "run_later", "recurring", "event_triggered"
    run_at: datetime | None = None
    recurrence_pattern: str | None = None  # cron pattern
    
    # Metadata context
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowApproval(BaseModel):
    """Tracks the state of a user approval task for a workflow step."""

    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    step_id: str
    status: str = "pending"  # "pending", "approved", "rejected", "modified", "delegated", "postponed"
    reason: str
    delegate_to: str | None = None
    postpone_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
