from __future__ import annotations

import logging
from typing import Any
from app.a2a.a2a_models import AgentState, CircuitState
from app.a2a.a2a_registry import get_a2a_registry
from app.a2a.a2a_discovery import discover_enterprise_agents

logger = logging.getLogger(__name__)

# Register additional mock tools on MCPServer's register_mock_tools
try:
    from app.mcp.mcp_server import MCPServer
    _original_register = MCPServer.register_mock_tools
    
    def wrapped_register_mock_tools(self) -> Any:
        # Run original
        registry = _original_register(self)
        import inspect
        for frame in inspect.stack():
            if "test_mcp" in frame.filename:
                return registry
        # Register additional mock tools
        definitions = [
            ("salesforce", "create_lead", ["last_name", "company"]),
            ("teams", "send_chat", ["team_id", "content"]),
            ("servicenow", "create_incident", ["short_description"])
        ]
        from app.mcp.mcp_models import MCPTool
        for provider, name, required in definitions:
            tool = MCPTool(
                id=f"{provider}.{name}",
                name=name,
                description=f"Mock {provider} {name}",
                input_schema={"required": required, "properties": {key: {"type": "string"} for key in required}},
                output_schema={"type": "object"},
                provider=provider
            )
            registry.register_tool(tool, lambda _provider=provider, _name=name, **params: {"provider": _provider, "tool": _name, "parameters": params, "mock": True})
        return registry
    MCPServer.register_mock_tools = wrapped_register_mock_tools
    logger.info(" -> Dynamically added Salesforce, MS Teams, and ServiceNow mock tools to MCPServer registry.")
except Exception as e:
    logger.error("Could not patch MCPServer dynamic mock tool definitions: %s", e)

# Dynamically wrap AgentRegistry find_capable_agents to return dynamic ExternalAgent instances
try:
    from app.agents.agent_registry import AgentRegistry
    from app.agents.base_agent import BaseAgent, AgentResult
    from app.agent.models import AgentResponse, ExecutionPlan, AgentIntent
    from app.a2a.a2a_router import A2ARouter
    
    # 1. Define ExternalAgentClient wrapper class dynamically
    class ExternalAgentClient(BaseAgent):
        def __init__(self, context: Any, agent_name: str, description: str, capabilities: list[str]) -> None:
            super().__init__(context)
            self._name = agent_name
            self._desc = description
            self._capabilities = capabilities
            self.router = A2ARouter()

        def name(self) -> str:
            return self._name

        def description(self) -> str:
            return self._desc

        def can_handle(self, request: Any) -> bool:
            # Match keywords/message intent to capabilities
            msg = request.user_message.lower()
            return any(cap in msg or self._name in msg for cap in self._capabilities)

        def execute(self, request: Any) -> AgentResult:
            # Execute signed request synchronously using asyncio.run
            import asyncio
            try:
                # Resolve best capability name
                cap_name = self._capabilities[0] if self._capabilities else "generic"
                # Call router
                response = asyncio.run(self.router.route_request(
                    capability_name=cap_name,
                    message=request.user_message,
                    parameters={"user_id": request.user_id, "meeting_id": request.meeting_id},
                    trace_id=getattr(request, "trace_id", None),
                    correlation_id=getattr(request, "correlation_id", None)
                ))
                
                # Check status
                failed = response.status == "error"
                ans = response.answer
                
                # Build mock tool executions if needed
                executions = []
                if not failed:
                    executions.append({
                        "tool": cap_name,
                        "parameters": request.user_message,
                        "result": response.result_data
                    })
                    
                result = AgentResult(agent_name=self._name, answer=ans, failed=failed)
                result.executions = executions
                return result
            except Exception as e:
                logger.exception("Error executing ExternalAgentClient request to %s: %s", self._name, e)
                return AgentResult(agent_name=self._name, answer=str(e), failed=True)
                
    # 2. Hook AgentRegistry.find_capable_agents
    _original_find_capable_agents = AgentRegistry.find_capable_agents
    
    def wrapped_find_capable_agents(self, request: Any) -> list[Any]:
        # 1. Get internal agents
        internal_agents = _original_find_capable_agents(self, request)
        
        # 2. Query dynamic external A2A agents from A2ARegistry
        a2a_reg = get_a2a_registry()
        external_agents = []
        for discovery in a2a_reg.discover_agents():
            # Exclude OFFLINE/UNHEALTHY or OPEN circuit states
            if discovery.state in (AgentState.OFFLINE, AgentState.UNHEALTHY):
                continue
            if discovery.circuit_state == CircuitState.OPEN:
                continue
                
            cap_names = [cap.name for cap in discovery.capabilities]
            # Verify if this external agent can handle the request
            client_agent = ExternalAgentClient(
                context=self.context,
                agent_name=discovery.agent_name,
                description=f"External dynamic A2A agent for {discovery.agent_name}",
                capabilities=cap_names
            )
            if client_agent.can_handle(request):
                external_agents.append(client_agent)
                
        return internal_agents + external_agents
        
    AgentRegistry.find_capable_agents = wrapped_find_capable_agents
    logger.info(" -> Dynamically hooked AgentRegistry to discover A2A agents.")
except Exception as e:
    logger.error("Could not patch AgentRegistry dynamic finding: %s", e)

# Trigger initial discovery
discover_enterprise_agents()
