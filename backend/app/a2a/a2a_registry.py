from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from app.a2a.a2a_models import AgentDiscovery, AgentCapability, AgentState, CircuitState

logger = logging.getLogger(__name__)

# Max failures before tripping circuit breaker
CIRCUIT_FAILURE_THRESHOLD = 3
# Cooldown seconds before moving circuit breaker from OPEN to HALF_OPEN
CIRCUIT_COOLDOWN_SECONDS = 30.0
# Heartbeat timeout before marking an agent as OFFLINE
HEARTBEAT_TIMEOUT_SECONDS = 60.0

class A2ARegistry:
    _instance: A2ARegistry | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._agents: dict[str, AgentDiscovery] = {}
        self._initialized = True

    def register_agent(
        self,
        agent_name: str,
        endpoint_url: str,
        capabilities: list[AgentCapability],
        version: str
    ) -> AgentDiscovery:
        """Register a discovered agent or update its capabilities."""
        now = datetime.now(timezone.utc)
        discovery = AgentDiscovery(
            agent_name=agent_name,
            endpoint_url=endpoint_url,
            capabilities=capabilities,
            version=version,
            state=AgentState.REGISTERING,
            circuit_state=CircuitState.CLOSED,
            consecutive_failures=0,
            last_state_change=now,
            last_heartbeat=now,
            metrics={
                "calls": 0,
                "latency_ms": 0.0,
                "success_rate": 1.0,
                "load": 0
            }
        )
        self._agents[agent_name] = discovery
        logger.info("A2A Agent Registered: %s at %s", agent_name, endpoint_url)
        return discovery

    def discover_agents(self) -> list[AgentDiscovery]:
        """Return list of all registered agents, checking for heartbeat timeouts first."""
        self.check_heartbeats()
        return list(self._agents.values())

    def get_agent(self, agent_name: str) -> AgentDiscovery | None:
        """Get an agent by name, updating heartbeat status first."""
        self.check_heartbeats()
        return self._agents.get(agent_name)

    def heartbeat(self, agent_name: str, status: AgentState = AgentState.ACTIVE, metrics: dict[str, Any] | None = None) -> bool:
        """Receive heartbeat signal, updating state and metrics."""
        agent = self._agents.get(agent_name)
        if not agent:
            logger.warning("Heartbeat received for unregistered agent: %s", agent_name)
            return False

        now = datetime.now(timezone.utc)
        agent.last_heartbeat = now
        
        # If agent was OFFLINE or REGISTERING, transition to ACTIVE or the reported status
        if agent.state in (AgentState.OFFLINE, AgentState.REGISTERING):
            self.update_status(agent_name, status)
        else:
            # Update to whatever the heartbeat reports unless we override it for unhealthy/degraded
            if agent.state not in (AgentState.UNHEALTHY, AgentState.RETIRING):
                agent.state = status

        if metrics:
            agent.metrics.update(metrics)

        # If circuit breaker was OPEN, check if cooldown elapsed to transition to HALF_OPEN
        if agent.circuit_state == CircuitState.OPEN:
            elapsed = (now - agent.last_state_change).total_seconds()
            if elapsed >= CIRCUIT_COOLDOWN_SECONDS:
                agent.circuit_state = CircuitState.HALF_OPEN
                agent.last_state_change = now
                logger.info("Circuit breaker for %s transitioned to HALF_OPEN on heartbeat cooldown", agent_name)

        return True

    def update_status(self, agent_name: str, new_state: AgentState) -> None:
        """Transition agent to a new lifecycle state."""
        agent = self._agents.get(agent_name)
        if agent and agent.state != new_state:
            old_state = agent.state
            agent.state = new_state
            agent.last_state_change = datetime.now(timezone.utc)
            logger.info("Agent state transition: agent=%s state=[%s -> %s]", agent_name, old_state, new_state)

    def record_failure(self, agent_name: str) -> None:
        """Track failure count to trip the circuit breaker if it exceeds the threshold."""
        agent = self._agents.get(agent_name)
        if not agent:
            return

        agent.consecutive_failures += 1
        logger.warning("A2A failure recorded for %s. Consecutive failures: %d", agent_name, agent.consecutive_failures)
        
        if agent.circuit_state == CircuitState.CLOSED and agent.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
            agent.circuit_state = CircuitState.OPEN
            agent.state = AgentState.DEGRADED
            agent.last_state_change = datetime.now(timezone.utc)
            logger.error("Circuit breaker TRIPPED to OPEN for agent: %s due to failures", agent_name)

    def record_success(self, agent_name: str) -> None:
        """Reset failure count and close the circuit breaker on success."""
        agent = self._agents.get(agent_name)
        if not agent:
            return

        agent.consecutive_failures = 0
        if agent.circuit_state == CircuitState.HALF_OPEN:
            agent.circuit_state = CircuitState.CLOSED
            agent.state = AgentState.ACTIVE
            agent.last_state_change = datetime.now(timezone.utc)
            logger.info("Circuit breaker CLOSED for agent %s after successful recovery request", agent_name)

    def remove_agent(self, agent_name: str) -> None:
        """De-register an agent from the registry."""
        self._agents.pop(agent_name, None)
        logger.info("A2A Agent Removed: %s", agent_name)

    def check_heartbeats(self) -> None:
        """Check all registered agents and transition them to OFFLINE if heartbeat is missing."""
        now = datetime.now(timezone.utc)
        for agent in self._agents.values():
            if agent.state != AgentState.OFFLINE:
                elapsed = (now - agent.last_heartbeat).total_seconds()
                if elapsed >= HEARTBEAT_TIMEOUT_SECONDS:
                    logger.warning("Heartbeat timeout for agent: %s. Setting to OFFLINE.", agent.agent_name)
                    self.update_status(agent.agent_name, AgentState.OFFLINE)


def get_a2a_registry() -> A2ARegistry:
    return A2ARegistry()
