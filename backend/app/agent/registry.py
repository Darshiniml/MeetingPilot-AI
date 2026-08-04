"""Generic in-memory registry for agent tools."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from .context import AgentContext
from .exceptions import ToolNotFoundException
from .tools import ALL_TOOL_TYPES
from .tools.base_tool import BaseTool, ServiceFactory

Tool = Callable[..., Any] | Any
logger = logging.getLogger(__name__)


class ToolRegistry:
    """Stores standalone tools without coupling to application services."""

    def __init__(self, services: Mapping[str, Any] | None = None, service_factories: Mapping[str, ServiceFactory] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        services = services or {}
        service_factories = service_factories or {}
        for tool_type in ALL_TOOL_TYPES:
            prototype = tool_type()
            name = prototype.name()
            self.register(name, tool_type(services.get(name), service_factories.get(name)))

    def register(self, name: str, tool: Tool) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Tool names must be non-empty strings.")
        if not callable(tool) and not callable(getattr(tool, "execute", None)):
            raise TypeError("A tool must be callable or expose an execute method.")
        self._tools[name] = tool

    def unregister(self, name: str) -> Tool | None:
        return self._tools.pop(name, None)

    def get_tool(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as error:
            raise ToolNotFoundException(f"Tool not found: {name}") from error

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, context: AgentContext, **parameters: Any) -> Any:
        return self.execute_tool(name, context, parameters)

    def execute_tool(self, name: str, context: AgentContext, parameters: Mapping[str, Any] | None = None) -> Any:
        """Execute one registered tool and log its outcome and duration."""
        started_at = perf_counter()
        parameters = dict(parameters or {})
        tool = self.get_tool(name)
        try:
            if isinstance(tool, BaseTool):
                result = tool.execute(context, parameters)
            else:
                executor = tool if callable(tool) else tool.execute
                result = executor(context=context, **parameters)
        except Exception:
            logger.exception("Agent tool failed: %s (%.2f ms)", name, (perf_counter() - started_at) * 1000)
            raise
        logger.info("Agent tool succeeded: %s (%.2f ms)", name, (perf_counter() - started_at) * 1000)
        return result

    def execute_tools(self, names: list[str], context: AgentContext, parameters: Mapping[str, Any] | None = None) -> list[Any]:
        """Execute tools in the supplied order."""
        return [self.execute_tool(name, context, parameters) for name in names]
