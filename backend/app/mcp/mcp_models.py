from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class MCPTool(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    provider: str
    version: str = "1.0"


class MCPRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    user_id: int
    conversation_id: str | None = None


class MCPResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str
    success: bool
    output: Any = None
    error: str | None = None
    execution_time: float = Field(ge=0.0)
