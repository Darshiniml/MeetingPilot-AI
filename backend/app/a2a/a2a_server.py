from __future__ import annotations

import time
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from app.a2a.a2a_models import AgentRequest, AgentResponse, AgentHeartbeat, AgentDiscovery, AgentCapability
from app.a2a.a2a_security import validate_request_security, sign_response
from app.a2a.a2a_registry import get_a2a_registry
from app.a2a.a2a_protocol import A2AProtocol
from app.a2a.a2a_metrics import get_a2a_metrics

logger = logging.getLogger(__name__)

a2a_router = APIRouter(prefix="/api/a2a", tags=["Agent-to-Agent"])

@a2a_router.post("/request", response_model=AgentResponse)
async def process_a2a_request(request: AgentRequest) -> AgentResponse:
    """Accept and process a signed A2A request from a peer agent."""
    # 1. Validate security properties (signature, nonce, skew)
    is_valid, error_msg = validate_request_security(request)
    if not is_valid:
        logger.error("A2A security validation failed: %s", error_msg)
        raise HTTPException(status_code=401, detail=f"Unauthorized: {error_msg}")

    logger.info("Processing secure A2A request from %s for %s", request.sender_name, request.receiver_name)

    # 2. Map and route to local agent logic
    # Since this is a modular integration, we support dynamic mock handling
    # and link to internal specialized agents.
    answer = f"Hello from MeetingPilot {request.receiver_name} agent! Message received: '{request.message}'"
    result_data: dict[str, Any] = {"status": "processed", "sender": request.sender_name}

    # Prepare response payload
    response = AgentResponse(
        request_id=request.request_id,
        trace_id=request.trace_id,
        correlation_id=request.correlation_id,
        sender_name=request.receiver_name,
        status="success",
        answer=answer,
        result_data=result_data,
        timestamp=time.time(),
        signature=""
    )
    
    # Sign response
    response.signature = sign_response(response)
    return response

@a2a_router.post("/heartbeat")
async def process_heartbeat(heartbeat: AgentHeartbeat) -> dict[str, str]:
    """Receive and record a heartbeat status check from an agent."""
    registry = get_a2a_registry()
    success = registry.heartbeat(
        agent_name=heartbeat.agent_name,
        status=heartbeat.status,
        metrics=heartbeat.metrics
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{heartbeat.agent_name}' not registered.")
    return {"status": "ok"}

@a2a_router.get("/discovery")
async def process_discovery() -> list[dict[str, Any]]:
    """Return capability schemas of all currently registered agents."""
    registry = get_a2a_registry()
    agents = registry.discover_agents()
    return [A2AProtocol.negotiate_capabilities(agent) for agent in agents]

@a2a_router.post("/register")
async def register_external_agent(discovery: AgentDiscovery) -> dict[str, str]:
    """Register an external agent into the registry dynamically."""
    registry = get_a2a_registry()
    registry.register_agent(
        agent_name=discovery.agent_name,
        endpoint_url=discovery.endpoint_url,
        capabilities=discovery.capabilities,
        version=discovery.version
    )
    # Perform immediate heartbeat update
    registry.heartbeat(discovery.agent_name, discovery.state, discovery.metrics)
    return {"status": "registered"}

@a2a_router.get("/metrics")
async def get_a2a_metrics_summary() -> dict[str, Any]:
    """Retrieve operational metrics of A2A transactions."""
    return get_a2a_metrics().get_stats()
