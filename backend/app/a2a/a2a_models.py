from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    REGISTERING = "REGISTERING"
    ACTIVE = "ACTIVE"
    BUSY = "BUSY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNHEALTHY = "UNHEALTHY"
    RETIRING = "RETIRING"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class LoadBalanceStrategy(str, Enum):
    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_LOADED = "LEAST_LOADED"
    LOWEST_LATENCY = "LOWEST_LATENCY"
    HIGHEST_SUCCESS = "HIGHEST_SUCCESS"


class AgentCapability(BaseModel):
    capability_id: str
    name: str
    version: str
    provider: str
    required_permissions: list[str] = Field(default_factory=list)
    supported_input_schema: dict[str, Any] = Field(default_factory=dict)
    supported_output_schema: dict[str, Any] = Field(default_factory=dict)
    health_status: str = "healthy"


class AgentDiscovery(BaseModel):
    agent_name: str
    endpoint_url: str
    capabilities: list[AgentCapability] = Field(default_factory=list)
    version: str
    state: AgentState = AgentState.REGISTERING
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_state_change: datetime = Field(default_factory=datetime.now)
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    metrics: dict[str, Any] = Field(default_factory=dict)


class AgentRequest(BaseModel):
    request_id: str
    trace_id: str
    correlation_id: str
    sender_name: str
    receiver_name: str
    message: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    nonce: str
    signature: str


class AgentResponse(BaseModel):
    request_id: str
    trace_id: str
    correlation_id: str
    sender_name: str
    status: str  # "success" or "error"
    answer: str
    result_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    signature: str


class AgentMessage(BaseModel):
    message_id: str
    sender: str
    receiver: str
    content: str
    conversation_id: str | None = None


class AgentHeartbeat(BaseModel):
    agent_name: str
    timestamp: float
    status: AgentState = AgentState.ACTIVE
    metrics: dict[str, Any] = Field(default_factory=dict)


class CrossAgentReference(BaseModel):
    ref_type: str  # "memory", "workflow", "meeting", "transcript", "document"
    ref_id: str
    source_agent: str
    metadata: dict[str, Any] = Field(default_factory=dict)
