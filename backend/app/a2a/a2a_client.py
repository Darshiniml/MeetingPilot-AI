from __future__ import annotations

import time
import uuid
import logging
import asyncio
from typing import AsyncGenerator
from app.a2a.a2a_models import AgentRequest, AgentResponse
from app.a2a.a2a_security import sign_request, verify_response_signature
from app.a2a.a2a_registry import get_a2a_registry

logger = logging.getLogger(__name__)

class A2AClient:
    def __init__(self, sender_name: str = "supervisor") -> None:
        self.sender_name = sender_name
        self.registry = get_a2a_registry()

    async def send_request(
        self,
        receiver_name: str,
        message: str,
        parameters: dict | None = None,
        timeout: float = 5.0,
        trace_id: str | None = None,
        correlation_id: str | None = None
    ) -> AgentResponse:
        """Send a signed A2A request to an agent with trace tracking, timeouts, and circuit breaker recording."""
        parameters = parameters or {}
        trace_id = trace_id or f"tr-{uuid.uuid4()}"
        correlation_id = correlation_id or f"corr-{uuid.uuid4()}"
        request_id = f"req-{uuid.uuid4()}"
        nonce = f"nonce-{uuid.uuid4().hex}"
        timestamp = time.time()

        agent_request = AgentRequest(
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            sender_name=self.sender_name,
            receiver_name=receiver_name,
            message=message,
            parameters=parameters,
            timestamp=timestamp,
            nonce=nonce,
            signature=""
        )
        agent_request.signature = sign_request(agent_request)

        # Retrieve registry entry to perform circuit breaker check
        discovery = self.registry.get_agent(receiver_name)
        if discovery and discovery.state == "DEGRADED" and discovery.circuit_state == "OPEN":
            logger.warning("A2A Request BLOCKED by Circuit Breaker for agent: %s", receiver_name)
            return AgentResponse(
                request_id=request_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                sender_name=receiver_name,
                status="error",
                answer=f"Circuit Breaker is OPEN for {receiver_name}.",
                timestamp=time.time(),
                signature=""
            )

        # Simulate network delay/HTTP request or mock dispatching
        try:
            # We wrap execution in asyncio.wait_for for timeout enforcement
            response = await asyncio.wait_for(
                self._dispatch_mock_request(agent_request),
                timeout=timeout
            )
            
            # Verify signature of the received response
            if response.status == "success" and not verify_response_signature(response):
                logger.error("Security failure: received invalid response signature from %s", receiver_name)
                self.registry.record_failure(receiver_name)
                response.status = "error"
                response.answer = "Security validation failed on received response signature."
            else:
                self.registry.record_success(receiver_name)

            return response
            
        except asyncio.TimeoutError:
            logger.error("A2A request timed out after %.2fs to %s", timeout, receiver_name)
            self.registry.record_failure(receiver_name)
            return AgentResponse(
                request_id=request_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                sender_name=receiver_name,
                status="error",
                answer=f"Request to {receiver_name} timed out after {timeout}s.",
                timestamp=time.time(),
                signature=""
            )
        except Exception as e:
            logger.exception("Error executing A2A request to %s: %s", receiver_name, e)
            self.registry.record_failure(receiver_name)
            return AgentResponse(
                request_id=request_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                sender_name=receiver_name,
                status="error",
                answer=f"Failed to communicate with {receiver_name}: {str(e)}.",
                timestamp=time.time(),
                signature=""
            )

    async def stream_request(
        self,
        receiver_name: str,
        message: str,
        parameters: dict | None = None
    ) -> AsyncGenerator[str, None]:
        """Support streaming partial text responses chunk-by-chunk for long running queries."""
        # Check circuit state
        discovery = self.registry.get_agent(receiver_name)
        if discovery and discovery.state == "DEGRADED" and discovery.circuit_state == "OPEN":
            yield f"Error: Circuit Breaker is OPEN for {receiver_name}."
            return

        # Simulate stream generation
        chunks = [
            f"[{receiver_name.upper()}] Initiated connection...",
            f"[{receiver_name.upper()}] Searching databases for query: '{message}'...",
            f"[{receiver_name.upper()}] Fetching entity references...",
            f"[{receiver_name.upper()}] Formulating final response payload..."
        ]
        
        for chunk in chunks:
            await asyncio.sleep(0.1)  # small simulated delay
            yield chunk

    async def _dispatch_mock_request(self, request: AgentRequest) -> AgentResponse:
        """Simulate local/in-process network handling of request to mock agent."""
        # Yield processing time simulation
        await asyncio.sleep(0.05)
        
        # If testing error behavior
        if "simulated_error" in request.message and request.receiver_name.endswith("1"):
            raise RuntimeError("Network communication failed")
            
        if "simulated_timeout" in request.message and request.receiver_name.endswith("1"):
            await asyncio.sleep(10.0) # trigger timeout

        # Standard successful response mock
        res_data = {"processed_by": request.receiver_name, "inputs": request.parameters}
        
        # Formulate signed response
        agent_response = AgentResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            sender_name=request.receiver_name,
            status="success",
            answer=f"Mock response from {request.receiver_name} for message: '{request.message}'",
            result_data=res_data,
            timestamp=time.time(),
            signature=""
        )
        # Sign it
        from app.a2a.a2a_security import sign_response
        agent_response.signature = sign_response(agent_response)
        return agent_response
