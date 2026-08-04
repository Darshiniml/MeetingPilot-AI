"""In-process mock MCP providers; no real external APIs are used."""

from __future__ import annotations

from typing import Any

from .mcp_models import MCPTool
from .mcp_registry import MCPRegistry


class MCPServer:
    def __init__(self, registry: MCPRegistry | None = None) -> None:
        self.registry = registry or MCPRegistry()

    def register_mock_tools(self) -> MCPRegistry:
        definitions = [
            ("github", "search_issues", ["query"]), ("github", "create_issue", ["title"]), ("github", "list_prs", []),
            ("slack", "send_message", ["channel", "message"]), ("slack", "list_channels", []),
            ("notion", "create_page", ["title"]), ("notion", "search_notes", ["query"]),
            ("google_drive", "search_files", ["query"]), ("jira", "search_issues", ["query"]),
        ]
        for provider, name, required in definitions:
            tool = MCPTool(id=f"{provider}.{name}", name=name, description=f"Mock {provider} {name}", input_schema={"required": required, "properties": {key: {"type": "string"} for key in required}}, output_schema={"type": "object"}, provider=provider)
            self.registry.register_tool(tool, lambda _provider=provider, _name=name, **params: {"provider": _provider, "tool": _name, "parameters": params, "mock": True})
        return self.registry
