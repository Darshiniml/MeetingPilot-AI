"""Typed contracts used by the autonomous agent framework."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentIntent(str, Enum):
    """Intents supported by the deterministic milestone-one planner."""

    SUMMARIZE_MEETING = "SUMMARIZE_MEETING"
    LIST_ACTION_ITEMS = "LIST_ACTION_ITEMS"
    SCHEDULE_MEETING = "SCHEDULE_MEETING"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    SEND_EMAIL = "SEND_EMAIL"
    CONTACT_SEARCH = "CONTACT_SEARCH"
    SEARCH_HISTORY = "SEARCH_HISTORY"
    SEARCH_TRANSCRIPT = "SEARCH_TRANSCRIPT"
    GENERAL_CHAT = "GENERAL_CHAT"


class AgentRequest(BaseModel):
    """Input accepted by :class:`AgentController`."""

    model_config = ConfigDict(frozen=True)

    user_message: str = Field(..., min_length=1)
    user_id: int
    meeting_id: int | None = None
    conversation_id: str | None = None


class ExecutionPlan(BaseModel):
    """The planner's explicit, inspectable execution decision."""

    model_config = ConfigDict(frozen=True)

    intent: AgentIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    tools: list[str] = Field(default_factory=list)
    reasoning: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolExecution(BaseModel):
    """A single tool invocation and its measured outcome."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    status: str
    execution_time_ms: float = Field(..., ge=0.0)
    output: Any = None


class AgentResponse(BaseModel):
    """Structured result returned by the controller."""

    model_config = ConfigDict(frozen=True)

    answer: str
    execution_plan: ExecutionPlan
    tool_executions: list[ToolExecution] = Field(default_factory=list)
    total_execution_time: float = Field(..., ge=0.0)
