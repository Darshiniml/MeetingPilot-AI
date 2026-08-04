"""Typed in-memory records for autonomous-agent memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReflectionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    reflection: str
    confidence_adjustment: float = Field(ge=-1.0, le=1.0)
    future_recommendations: list[str] = Field(default_factory=list)


class ConversationInteraction(BaseModel):
    """One completed agent interaction retained in conversation memory."""

    model_config = ConfigDict(frozen=True)

    user_message: str
    planner_decision: dict[str, Any]
    tool_outputs: dict[str, Any] = Field(default_factory=dict)
    agent_response: str
    reflection: ReflectionRecord
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
