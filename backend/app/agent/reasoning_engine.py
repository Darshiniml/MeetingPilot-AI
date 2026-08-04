"""Sequential tool execution with explicit shared execution state."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from .context import AgentContext
from .exceptions import ToolNotFoundException
from .memory import WorkingMemory
from .models import ExecutionPlan, ToolExecution
from .registry import ToolRegistry

logger = logging.getLogger(__name__)
_REFERENCE = re.compile(r"\{\{(?P<path>(?:tool_outputs|shared_variables)\.[\w.]+)\}\}")


@dataclass
class ExecutionContext:
    """Mutable per-request state shared across sequential tool calls."""

    tool_outputs: dict[str, Any] = field(default_factory=dict)
    shared_variables: dict[str, Any] = field(default_factory=dict)
    conversation_memory: list[dict[str, Any]] = field(default_factory=list)


class ReasoningEngine:
    """Executes planned tools in order, exposing earlier outputs to later calls."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(
        self, plan: ExecutionPlan, context: AgentContext, execution_context: ExecutionContext | None = None, working_memory: WorkingMemory | None = None
    ) -> tuple[list[ToolExecution], ExecutionContext]:
        state = execution_context or ExecutionContext()
        state.shared_variables.update(plan.parameters)
        executions: list[ToolExecution] = []

        for tool_name in plan.tools:
            started_at = perf_counter()
            parameters = self._resolve(plan.parameters, state)
            try:
                output = self._registry.execute_tool(tool_name, context, parameters)
            except ToolNotFoundException:
                execution = ToolExecution(tool_name=tool_name, status="missing", execution_time_ms=(perf_counter() - started_at) * 1000, output="Tool not yet registered")
            except Exception as error:
                logger.exception("Reasoning engine tool failure: %s", tool_name)
                execution = ToolExecution(tool_name=tool_name, status="failed", execution_time_ms=(perf_counter() - started_at) * 1000, output=str(error))
            else:
                state.tool_outputs[tool_name] = output
                if isinstance(output, dict):
                    state.shared_variables.update(output)
                if working_memory is not None:
                    working_memory.update_tool_output(tool_name, output)
                execution = ToolExecution(tool_name=tool_name, status="completed", execution_time_ms=(perf_counter() - started_at) * 1000, output=output)
            executions.append(execution)
            state.conversation_memory.append({"tool": tool_name, "status": execution.status, "output": execution.output})
            logger.info("Reasoning engine executed %s with status %s", tool_name, execution.status)
        return executions, state

    def _resolve(self, value: Any, state: ExecutionContext) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve(item, state) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve(item, state) for item in value]
        if not isinstance(value, str):
            return value
        full_match = _REFERENCE.fullmatch(value)
        if full_match:
            try:
                return self._lookup(full_match.group("path"), state)
            except (AttributeError, KeyError):
                return value

        def replace(match: re.Match[str]) -> str:
            try:
                return str(self._lookup(match.group("path"), state))
            except (AttributeError, KeyError):
                return match.group(0)

        return _REFERENCE.sub(replace, value)

    @staticmethod
    def _lookup(path: str, state: ExecutionContext) -> Any:
        root, *keys = path.split(".")
        value: Any = state.tool_outputs if root == "tool_outputs" else state.shared_variables
        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            else:
                value = getattr(value, key)
        return value
