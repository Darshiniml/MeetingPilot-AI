from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    sender: str
    receiver: str | None = None
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    conversation_id: str | None = None
