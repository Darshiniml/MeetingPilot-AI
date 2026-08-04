from __future__ import annotations

from .mcp_exceptions import MCPValidationException
from .mcp_models import MCPTool


def validate_parameters(tool: MCPTool, parameters: dict) -> None:
    """Validate the compact JSON-schema subset used by in-process mock tools."""
    schema = tool.input_schema
    for key in schema.get("required", []):
        if key not in parameters: raise MCPValidationException(f"Missing required parameter: {key}")
    for key, spec in schema.get("properties", {}).items():
        if key in parameters and spec.get("type") == "string" and not isinstance(parameters[key], str):
            raise MCPValidationException(f"Parameter {key} must be a string")
