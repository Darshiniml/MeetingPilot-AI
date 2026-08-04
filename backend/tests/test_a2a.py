from __future__ import annotations

import unittest
import asyncio
import time
from unittest.mock import MagicMock
from app.a2a.a2a_models import (
    AgentCapability, AgentDiscovery, AgentState, CircuitState,
    LoadBalanceStrategy, AgentRequest, AgentResponse, CrossAgentReference
)
from app.a2a.a2a_registry import get_a2a_registry
from app.a2a.a2a_security import validate_request_security, sign_request
from app.a2a.a2a_client import A2AClient
from app.a2a.a2a_router import A2ARouter, routing_decision_logs
from app.a2a.a2a_protocol import A2AProtocol
from app.a2a.a2a_metrics import get_a2a_metrics
from app.agents.agent_registry import AgentRegistry
from app.agents.agent_context import AgentContext
from app.agent.models import AgentRequest as InternalAgentRequest


class A2ATests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_a2a_registry()
        self.registry._agents.clear()
        self.metrics = get_a2a_metrics()
        self.metrics.reset()
        routing_decision_logs.clear()

    def test_agent_registration_and_heartbeats(self) -> None:
        # Register a mock agent
        cap = AgentCapability(
            capability_id="test.hello",
            name="hello",
            version="1.0.0",
            provider="test",
            required_permissions=[],
            supported_input_schema={},
            supported_output_schema={},
            health_status="healthy"
        )
        self.registry.register_agent(
            agent_name="hello_agent",
            endpoint_url="http://mock-hello/api/a2a",
            capabilities=[cap],
            version="1.0.0"
        )

        agent = self.registry.get_agent("hello_agent")
        self.assertIsNotNone(agent)
        self.assertEqual(agent.state, AgentState.REGISTERING)

        # Heartbeat turns it ACTIVE
        self.registry.heartbeat("hello_agent", AgentState.ACTIVE, {"load": 5})
        self.assertEqual(agent.state, AgentState.ACTIVE)
        self.assertEqual(agent.metrics.get("load"), 5)

        # Heartbeat timeout check
        # Force last heartbeat to be in the past
        from datetime import datetime, timedelta, timezone
        agent.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=70)
        self.registry.check_heartbeats()
        self.assertEqual(agent.state, AgentState.OFFLINE)

    def test_circuit_breaker_behavior(self) -> None:
        cap = AgentCapability(
            capability_id="test.fail",
            name="fail",
            version="1.0.0",
            provider="test"
        )
        self.registry.register_agent(
            agent_name="fail_agent",
            endpoint_url="http://mock-fail/api/a2a",
            capabilities=[cap],
            version="1.0.0"
        )
        self.registry.heartbeat("fail_agent", AgentState.ACTIVE)

        agent = self.registry.get_agent("fail_agent")
        self.assertEqual(agent.circuit_state, CircuitState.CLOSED)

        # Record 3 failures to trip the circuit
        self.registry.record_failure("fail_agent")
        self.registry.record_failure("fail_agent")
        self.registry.record_failure("fail_agent")

        self.assertEqual(agent.circuit_state, CircuitState.OPEN)
        self.assertEqual(agent.state, AgentState.DEGRADED)

        # Request to circuit-broken agent should return error immediately
        client = A2AClient()
        response = asyncio.run(client.send_request("fail_agent", "hello"))
        self.assertEqual(response.status, "error")
        self.assertIn("Circuit Breaker is OPEN", response.answer)

        # Force state change time into past to trigger HALF_OPEN transition
        from datetime import datetime, timedelta, timezone
        agent.last_state_change = datetime.now(timezone.utc) - timedelta(seconds=40)
        self.registry.heartbeat("fail_agent", AgentState.ACTIVE)
        self.assertEqual(agent.circuit_state, CircuitState.HALF_OPEN)

        # Record success to close circuit
        self.registry.record_success("fail_agent")
        self.assertEqual(agent.circuit_state, CircuitState.CLOSED)

    def test_load_balancing_strategies(self) -> None:
        # Register two agents with same capability
        cap1 = AgentCapability(capability_id="a1.work", name="work", version="1.0.0", provider="a1")
        self.registry.register_agent("agent_1", "http://a1", [cap1], "1.0.0")
        self.registry.heartbeat("agent_1", AgentState.ACTIVE, {"load": 10, "latency_ms": 50.0, "success_rate": 0.99})

        cap2 = AgentCapability(capability_id="a2.work", name="work", version="1.0.0", provider="a2")
        self.registry.register_agent("agent_2", "http://a2", [cap2], "1.0.0")
        self.registry.heartbeat("agent_2", AgentState.ACTIVE, {"load": 2, "latency_ms": 150.0, "success_rate": 0.80})

        router = A2ARouter()

        # 1. Least Loaded should select agent_2
        selected, _, _ = router.select_best_agent("work", LoadBalanceStrategy.LEAST_LOADED)
        self.assertEqual(selected.agent_name, "agent_2")

        # 2. Lowest Latency should select agent_1
        selected, _, _ = router.select_best_agent("work", LoadBalanceStrategy.LOWEST_LATENCY)
        self.assertEqual(selected.agent_name, "agent_1")

        # 3. Highest Success should select agent_1
        selected, _, _ = router.select_best_agent("work", LoadBalanceStrategy.HIGHEST_SUCCESS)
        self.assertEqual(selected.agent_name, "agent_1")

        # 4. Round Robin alternating
        selected, _, _ = router.select_best_agent("work", LoadBalanceStrategy.ROUND_ROBIN)
        self.assertEqual(selected.agent_name, "agent_1")
        selected, _, _ = router.select_best_agent("work", LoadBalanceStrategy.ROUND_ROBIN)
        self.assertEqual(selected.agent_name, "agent_2")

    def test_parallel_routing_and_fallbacks(self) -> None:
        cap1 = AgentCapability(capability_id="a1.run", name="run", version="1.0.0", provider="a1")
        self.registry.register_agent("runner_1", "http://a1", [cap1], "1.0.0")
        self.registry.heartbeat("runner_1", AgentState.ACTIVE, {"load": 1, "latency_ms": 10.0, "success_rate": 0.9})

        cap2 = AgentCapability(capability_id="a2.run", name="run", version="1.0.0", provider="a2")
        self.registry.register_agent("runner_2", "http://a2", [cap2], "1.0.0")
        self.registry.heartbeat("runner_2", AgentState.ACTIVE, {"load": 2, "latency_ms": 10.0, "success_rate": 0.9})

        router = A2ARouter()

        # Parallel routing dispatches to all
        responses = asyncio.run(router.route_parallel("run", "perform sprint"))
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].status, "success")
        self.assertEqual(responses[1].status, "success")

        # Fallback test: runner_1 fails (or simulates error)
        # Call with simulated_error
        res = asyncio.run(router.route_request("run", "simulated_error", strategy=LoadBalanceStrategy.LOWEST_LATENCY))
        self.assertEqual(res.status, "success")
        # Assert that the decision log logged "fallback_success"
        self.assertTrue(any(log["result"] == "fallback_success" for log in routing_decision_logs))

    def test_distributed_tracing_propagation(self) -> None:
        cap = AgentCapability(capability_id="a.trace", name="trace", version="1.0.0", provider="a")
        self.registry.register_agent("trace_agent", "http://trace", [cap], "1.0.0")
        self.registry.heartbeat("trace_agent", AgentState.ACTIVE)

        router = A2ARouter()
        res = asyncio.run(router.route_request("trace", "log transaction", trace_id="T123", correlation_id="C456"))
        self.assertEqual(res.status, "success")
        self.assertEqual(res.trace_id, "T123")
        self.assertEqual(res.correlation_id, "C456")

    def test_streaming_responses(self) -> None:
        client = A2AClient()
        
        async def read_stream():
            chunks = []
            async for chunk in client.stream_request("github", "search pull requests"):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(read_stream())
        self.assertEqual(len(chunks), 4)
        self.assertIn("[GITHUB] Initiated connection...", chunks[0])

    def test_security_validation_and_replay_protection(self) -> None:
        req = AgentRequest(
            request_id="req-sec",
            trace_id="tr-sec",
            correlation_id="corr-sec",
            sender_name="supervisor",
            receiver_name="slack",
            message="notify team",
            timestamp=time.time(),
            nonce="nonce-sec-1",
            signature=""
        )
        req.signature = sign_request(req)

        # 1. Success validation
        is_valid, msg = validate_request_security(req)
        self.assertTrue(is_valid, msg)

        # 2. Replay attack rejection (same nonce/timestamp)
        is_valid, msg = validate_request_security(req)
        self.assertFalse(is_valid)
        self.assertIn("Replay attack detected", msg)

        # 3. Time skew skew validation
        req_skew = AgentRequest(
            request_id="req-skew",
            trace_id="tr-skew",
            correlation_id="corr-skew",
            sender_name="supervisor",
            receiver_name="slack",
            message="notify team",
            timestamp=time.time() - 400.0,  # > 5 minutes skew
            nonce="nonce-skew",
            signature=""
        )
        req_skew.signature = sign_request(req_skew)
        is_valid, msg = validate_request_security(req_skew)
        self.assertFalse(is_valid)
        self.assertIn("skew window", msg)

    def test_cross_agent_references(self) -> None:
        ref = CrossAgentReference(
            ref_type="meeting",
            ref_id="meeting-42",
            source_agent="research",
            metadata={"title": "Planning Scrum"}
        )
        self.assertEqual(ref.ref_id, "meeting-42")
        self.assertEqual(ref.ref_type, "meeting")

    def test_supervisor_integration(self) -> None:
        # Setup context and registry
        context = MagicMock(spec=AgentContext)
        context.event_bus = MagicMock()
        context.metrics = MagicMock()
        
        # Instantiate AgentRegistry
        reg = AgentRegistry(context, auto_register=False)
        
        # Assert that find_capable_agents yields external client wrappers
        req = InternalAgentRequest(
            user_id=1,
            meeting_id=42,
            conversation_id="conv-1",
            user_message="Send a message to Slack detailing decisions"
        )
        
        # Register slack agent capability
        cap = AgentCapability(
            capability_id="slack.send_message",
            name="send_message",
            version="1.0.0",
            provider="slack"
        )
        self.registry.register_agent("slack", "http://slack", [cap], "1.0.0")
        self.registry.heartbeat("slack", AgentState.ACTIVE)
        
        capable = reg.find_capable_agents(req)
        capable_names = [agent.name() for agent in capable]
        self.assertIn("slack", capable_names)

        # Test capability negotiation mapping formats
        negotiated = A2AProtocol.negotiate_capabilities(self.registry.get_agent("slack"))
        self.assertEqual(negotiated["agent_name"], "slack")
        self.assertEqual(negotiated["capabilities"][0]["name"], "send_message")

        openai_schema = A2AProtocol.to_openai_tool_schema(cap)
        self.assertEqual(openai_schema["type"], "function")
        self.assertEqual(openai_schema["function"]["name"], "slack_send_message")
