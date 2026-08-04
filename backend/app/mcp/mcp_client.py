from __future__ import annotations

import logging
from collections import Counter
from time import perf_counter

from .mcp_exceptions import MCPToolNotFoundException, MCPTransientException
from .mcp_models import MCPRequest, MCPResponse, MCPTool
from .mcp_protocol import validate_parameters
from .mcp_registry import MCPRegistry

logger = logging.getLogger(__name__)


class MCPMetrics:
    def __init__(self) -> None:
        self.calls = self.successful_calls = self.failed_calls = 0
        self.total_latency = 0.0
        self.provider_usage: Counter[str] = Counter()
    def snapshot(self):
        return {"mcp_calls": self.calls, "successful_calls": self.successful_calls, "failed_calls": self.failed_calls, "average_latency": self.total_latency / self.calls if self.calls else 0.0, "provider_usage": dict(self.provider_usage)}


class MCPClient:
    def __init__(self, registry: MCPRegistry, metrics: MCPMetrics | None = None) -> None:
        self.registry, self.metrics = registry, metrics or MCPMetrics()

    def discover_tools(self, provider: str | None = None) -> list[MCPTool]:
        tools = self.registry.discover_tools(provider)
        logger.info("MCP discovery provider=%s count=%d", provider, len(tools))
        return tools

    def invoke(self, request: MCPRequest, provider: str | None = None, fallback_providers: list[str] | None = None) -> MCPResponse:
        candidates = [provider] if provider else [None]
        candidates.extend(item for item in (fallback_providers or []) if item not in candidates)
        started = perf_counter()
        error = None
        for candidate in candidates:
            found = self.registry.find_tool(request.tool_name, candidate)
            if not found:
                error = f"MCP tool unavailable: {request.tool_name}"; continue
            tool, handler = found
            self.metrics.calls += 1; self.metrics.provider_usage[tool.provider] += 1
            try:
                validate_parameters(tool, request.parameters)
                try:
                    output = handler(**request.parameters)
                except MCPTransientException:
                    logger.warning("MCP transient failure; retrying tool=%s", tool.name)
                    output = handler(**request.parameters)
                elapsed = (perf_counter() - started) * 1000
                self.metrics.successful_calls += 1; self.metrics.total_latency += elapsed
                logger.info("MCP call succeeded provider=%s tool=%s duration_ms=%.2f", tool.provider, tool.name, elapsed)
                return MCPResponse(request_id=request.request_id, success=True, output=output, execution_time=elapsed)
            except Exception as exc:
                error = str(exc); logger.exception("MCP call failed provider=%s tool=%s", tool.provider, tool.name)
        elapsed = (perf_counter() - started) * 1000
        self.metrics.failed_calls += 1; self.metrics.total_latency += elapsed
        return MCPResponse(request_id=request.request_id, success=False, error=error or "MCP tool unavailable", execution_time=elapsed)
