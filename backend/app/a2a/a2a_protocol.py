from __future__ import annotations

import logging
from typing import Any
from app.a2a.a2a_models import AgentCapability, AgentDiscovery

logger = logging.getLogger(__name__)

class A2AProtocol:
    """
    Standard helper class to structure metadata formats and negotiate capabilities
    across external SDKs (OpenAI, LangGraph, CrewAI, AutoGen, and MCP).
    """

    @staticmethod
    def negotiate_capabilities(discovery: AgentDiscovery) -> dict[str, Any]:
        """
        Produce capability negotiation summary output payload.
        Example response for: 'What capabilities do you support?'
        """
        return {
            "agent_name": discovery.agent_name,
            "version": discovery.version,
            "health_status": discovery.state,
            "circuit_state": discovery.circuit_state,
            "capabilities": [
                {
                    "capability_id": cap.capability_id,
                    "name": cap.name,
                    "version": cap.version,
                    "provider": cap.provider,
                    "required_permissions": cap.required_permissions,
                    "input_schema": cap.supported_input_schema,
                    "output_schema": cap.supported_output_schema,
                    "health": cap.health_status
                }
                for cap in discovery.capabilities
            ]
        }

    @staticmethod
    def validate_input_parameters(capability: AgentCapability, parameters: dict[str, Any]) -> tuple[bool, str]:
        """Verify parameters against capability's JSON input schema."""
        schema = capability.supported_input_schema
        if not schema:
            return True, "No input schema restriction."

        required = schema.get("required", [])
        for req in required:
            if req not in parameters:
                return False, f"Missing required parameter: '{req}'"

        properties = schema.get("properties", {})
        for key, val in parameters.items():
            prop = properties.get(key)
            if prop:
                expected_type = prop.get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return False, f"Parameter '{key}' type mismatch: expected string, got {type(val).__name__}."
                elif expected_type == "integer" and not isinstance(val, int):
                    return False, f"Parameter '{key}' type mismatch: expected integer, got {type(val).__name__}."
                elif expected_type == "array" and not isinstance(val, list):
                    return False, f"Parameter '{key}' type mismatch: expected list, got {type(val).__name__}."
                elif expected_type == "object" and not isinstance(val, dict):
                    return False, f"Parameter '{key}' type mismatch: expected dict, got {type(val).__name__}."

        return True, "Parameter validation successful."

    @staticmethod
    def to_openai_tool_schema(capability: AgentCapability) -> dict[str, Any]:
        """Map capability to OpenAI Agents Function Tool schema format."""
        return {
            "type": "function",
            "function": {
                "name": capability.capability_id.replace(".", "_"),
                "description": f"Invoke capability {capability.name} provided by {capability.provider}",
                "parameters": capability.supported_input_schema
            }
        }

    @staticmethod
    def to_langgraph_tool(capability: AgentCapability) -> dict[str, Any]:
        """Map capability to LangGraph state tool format representation."""
        return {
            "name": capability.capability_id,
            "description": f"Executes capability: {capability.name}",
            "args_schema": capability.supported_input_schema
        }
