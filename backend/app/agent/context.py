"""Request-scoped context supplied to every agent tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentContext(BaseModel):
    """Stable context shared by planning and future tool implementations."""

    model_config = ConfigDict(frozen=True)

    current_user: int
    active_meeting: int | None = None
    conversation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_metadata: dict[str, Any] = Field(default_factory=dict)
