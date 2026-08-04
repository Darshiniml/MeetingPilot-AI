"""Optional adapter used when a supervisor plan requests an external MCP tool."""

from __future__ import annotations

from app.agent.models import AgentRequest

from .mcp_client import MCPClient
from .mcp_models import MCPRequest, MCPResponse


class MCPSupervisorBridge:
    """Keeps existing SupervisorAgent untouched while enabling EXTERNAL_TOOL plans."""
    def __init__(self, client: MCPClient) -> None:
        self.client = client

    def execute_external_tool(self, request: AgentRequest, tool_name: str, parameters: dict, provider: str | None = None, fallback_providers: list[str] | None = None) -> MCPResponse:
        return self.client.invoke(MCPRequest(tool_name=tool_name, parameters=parameters, user_id=request.user_id, conversation_id=request.conversation_id), provider=provider, fallback_providers=fallback_providers)
