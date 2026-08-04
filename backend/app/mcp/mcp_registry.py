from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .mcp_models import MCPTool

logger = logging.getLogger(__name__)


class MCPRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[MCPTool, Callable[..., Any]]] = {}

    def register_tool(self, tool: MCPTool, handler: Callable[..., Any]) -> None:
        self._tools[tool.id] = (tool, handler)
        logger.info("MCP tool registered: provider=%s tool=%s", tool.provider, tool.name)

    def unregister_tool(self, tool_id: str) -> MCPTool | None:
        pair = self._tools.pop(tool_id, None)
        return None if pair is None else pair[0]

    def discover_tools(self, provider: str | None = None) -> list[MCPTool]:
        return [tool for tool, _ in self._tools.values() if provider is None or tool.provider == provider]

    def find_tool(self, name: str, provider: str | None = None) -> tuple[MCPTool, Callable[..., Any]] | None:
        for tool, handler in self._tools.values():
            if tool.name == name and (provider is None or tool.provider == provider): return tool, handler
        return None

    def list_providers(self) -> list[str]:
        return sorted({tool.provider for tool, _ in self._tools.values()})
