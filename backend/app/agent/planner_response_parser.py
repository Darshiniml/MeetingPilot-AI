"""Validation and conversion for structured planner responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .exceptions import PlannerException
from .models import AgentIntent, ExecutionPlan
from .prompt_templates import TOOL_CATALOG


class PlannerResponseParser:
    """Converts strict JSON returned by the LLM into an ExecutionPlan."""

    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self._allowed_tools = allowed_tools or {tool["name"] for tool in TOOL_CATALOG}

    def parse(self, response: str) -> ExecutionPlan:
        try:
            payload = json.loads(self._extract_json(response))
        except (TypeError, json.JSONDecodeError) as error:
            raise PlannerException("Planner response was not valid JSON.") from error
        if not isinstance(payload, dict):
            raise PlannerException("Planner response must be a JSON object.")

        intent = payload.get("intent")
        if intent == "MULTI_TOOL":
            # ExecutionPlan intentionally has no orchestration-only MULTI_TOOL enum member.
            payload["intent"] = AgentIntent.GENERAL_CHAT.value
        try:
            plan = ExecutionPlan.model_validate(payload)
        except ValidationError as error:
            raise PlannerException("Planner JSON did not match the execution plan contract.") from error
        unknown_tools = set(plan.tools) - self._allowed_tools
        if unknown_tools:
            raise PlannerException(f"Planner selected unknown tools: {sorted(unknown_tools)}")
        return plan

    @staticmethod
    def _extract_json(response: str) -> str:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            text = text.rsplit("```", 1)[0].strip()
        return text
