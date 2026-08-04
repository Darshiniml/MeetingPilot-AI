from __future__ import annotations

import time
import logging
import asyncio
from typing import Any
from app.a2a.a2a_models import AgentRequest, AgentResponse, LoadBalanceStrategy, AgentDiscovery, AgentState, CircuitState
from app.a2a.a2a_registry import get_a2a_registry
from app.a2a.a2a_client import A2AClient
from app.a2a.a2a_metrics import get_a2a_metrics

logger = logging.getLogger(__name__)

# Decision log list to support explainability
routing_decision_logs: list[dict[str, Any]] = []

class A2ARouter:
    def __init__(self, client: A2AClient | None = None) -> None:
        self.registry = get_a2a_registry()
        self.client = client or A2AClient()
        self.round_robin_counters: dict[str, int] = {}
        self.metrics = get_a2a_metrics()

    def select_best_agent(
        self,
        capability_name: str,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED
    ) -> tuple[AgentDiscovery | None, list[AgentDiscovery], str]:
        """
        Intelligently select the best agent mapping a capability according to strategy,
        excluding circuit-tripped (OPEN) and OFFLINE/UNHEALTHY agents.
        """
        agents = self.registry.discover_agents()
        candidates: list[AgentDiscovery] = []
        
        for agent in agents:
            # Check capability match
            has_cap = any(cap.name == capability_name for cap in agent.capabilities)
            if not has_cap:
                continue
                
            # Filter out OFFLINE, UNHEALTHY or OPEN circuit states
            if agent.state in (AgentState.OFFLINE, AgentState.UNHEALTHY):
                continue
            if agent.circuit_state == CircuitState.OPEN:
                continue
                
            candidates.append(agent)

        if not candidates:
            return None, [], "No healthy candidates exposing target capability."

        selected: AgentDiscovery | None = None
        reason = ""

        # Strategy selection
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            counter = self.round_robin_counters.get(capability_name, 0)
            selected = candidates[counter % len(candidates)]
            self.round_robin_counters[capability_name] = counter + 1
            reason = f"Selected via Round Robin (index {counter})"

        elif strategy == LoadBalanceStrategy.LEAST_LOADED:
            # Sort by metrics["load"] ascending
            selected = min(candidates, key=lambda a: a.metrics.get("load", 0))
            reason = f"Selected via Least Loaded (load={selected.metrics.get('load', 0)})"

        elif strategy == LoadBalanceStrategy.LOWEST_LATENCY:
            # Sort by metrics["latency_ms"] ascending
            selected = min(candidates, key=lambda a: a.metrics.get("latency_ms", 9999.0))
            reason = f"Selected via Lowest Latency (latency={selected.metrics.get('latency_ms', 0.0)}ms)"

        elif strategy == LoadBalanceStrategy.HIGHEST_SUCCESS:
            # Sort by metrics["success_rate"] descending
            selected = max(candidates, key=lambda a: a.metrics.get("success_rate", 0.0))
            reason = f"Selected via Highest Success Rate (success={selected.metrics.get('success_rate', 0.0)})"

        else:
            selected = candidates[0]
            reason = "Selected via default first-match strategy"

        alternatives = [c for c in candidates if c.agent_name != selected.agent_name]
        return selected, alternatives, reason

    async def route_request(
        self,
        capability_name: str,
        message: str,
        parameters: dict | None = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED,
        timeout: float = 5.0,
        trace_id: str | None = None,
        correlation_id: str | None = None
    ) -> AgentResponse:
        """Route request to primary selected agent, with parallel backup and fallback logic."""
        parameters = parameters or {}
        start_time = time.perf_counter()
        
        self.metrics.record_request()

        selected_agent, alternatives, selection_reason = self.select_best_agent(capability_name, strategy)
        
        if not selected_agent:
            # Decision logging for failure
            duration = (time.perf_counter() - start_time) * 1000
            decision = {
                "timestamp": time.time(),
                "capability": capability_name,
                "selected_agent": "None",
                "alternatives_considered": [],
                "reason": selection_reason,
                "duration_ms": duration,
                "result": "failed"
            }
            routing_decision_logs.append(decision)
            logger.error("A2A Routing failed: %s", selection_reason)
            return AgentResponse(
                request_id="nil",
                trace_id=trace_id or "nil",
                correlation_id=correlation_id or "nil",
                sender_name="router",
                status="error",
                answer=f"Routing failed: {selection_reason}",
                timestamp=time.time(),
                signature=""
            )

        logger.info("A2A Router: selected %s for %s (%s)", selected_agent.agent_name, capability_name, selection_reason)

        # Call primary agent
        response = await self.client.send_request(
            receiver_name=selected_agent.agent_name,
            message=message,
            parameters=parameters,
            timeout=timeout,
            trace_id=trace_id,
            correlation_id=correlation_id
        )

        duration = (time.perf_counter() - start_time) * 1000
        self.metrics.record_latency(duration)

        # Check if fallback is needed
        if response.status == "error":
            self.metrics.record_fallback()
            # Try fallback to next alternative
            fallback_agent = alternatives[0] if alternatives else None
            if fallback_agent:
                logger.warning("Primary agent %s failed; routing fallback to %s", selected_agent.agent_name, fallback_agent.agent_name)
                response = await self.client.send_request(
                    receiver_name=fallback_agent.agent_name,
                    message=message,
                    parameters=parameters,
                    timeout=timeout,
                    trace_id=trace_id,
                    correlation_id=correlation_id
                )
                
                decision_res = "fallback_success" if response.status == "success" else "fallback_failed"
                decision = {
                    "timestamp": time.time(),
                    "capability": capability_name,
                    "selected_agent": selected_agent.agent_name,
                    "fallback_agent": fallback_agent.agent_name,
                    "alternatives_considered": [alt.agent_name for alt in alternatives],
                    "reason": f"Primary failed. Fallback: {selection_reason}",
                    "duration_ms": (time.perf_counter() - start_time) * 1000,
                    "result": decision_res
                }
                routing_decision_logs.append(decision)
                return response
            else:
                logger.error("Primary agent %s failed and no fallback alternative is available.", selected_agent.agent_name)

        # Log decision on success or general failure
        decision = {
            "timestamp": time.time(),
            "capability": capability_name,
            "selected_agent": selected_agent.agent_name,
            "alternatives_considered": [alt.agent_name for alt in alternatives],
            "reason": selection_reason,
            "duration_ms": duration,
            "result": "success" if response.status == "success" else "failed"
        }
        routing_decision_logs.append(decision)
        
        if response.status == "success":
            self.metrics.record_success()
        
        return response

    async def route_parallel(
        self,
        capability_name: str,
        message: str,
        parameters: dict | None = None,
        timeout: float = 5.0
    ) -> list[AgentResponse]:
        """Dispatch a message to ALL healthy candidate agents exposing target capability in parallel."""
        parameters = parameters or {}
        agents = self.registry.discover_agents()
        candidates = [
            agent for agent in agents
            if any(cap.name == capability_name for cap in agent.capabilities)
            and agent.state not in (AgentState.OFFLINE, AgentState.UNHEALTHY)
            and agent.circuit_state != CircuitState.OPEN
        ]

        if not candidates:
            return []

        tasks = [
            self.client.send_request(
                receiver_name=agent.agent_name,
                message=message,
                parameters=parameters,
                timeout=timeout
            )
            for agent in candidates
        ]

        return list(await asyncio.gather(*tasks))
