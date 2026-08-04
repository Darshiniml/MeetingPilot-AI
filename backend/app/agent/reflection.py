"""Deterministic post-execution reflection for agent quality feedback."""

from __future__ import annotations

from .memory_models import ReflectionRecord
from .models import ExecutionPlan, ToolExecution


class ReflectionEngine:
    """Evaluates completed tool executions without changing tool behavior."""

    def reflect(self, plan: ExecutionPlan, executions: list[ToolExecution]) -> ReflectionRecord:
        missing = [item.tool_name for item in executions if item.status == "missing"]
        failed = [item.tool_name for item in executions if item.status == "failed"]
        if missing:
            return ReflectionRecord(
                reflection=f"Task was incomplete because unavailable tools were selected: {', '.join(missing)}.",
                confidence_adjustment=-0.3,
                future_recommendations=["Register the unavailable tools before retrying."],
            )
        if failed:
            return ReflectionRecord(
                reflection=f"Task was partially completed; failed tools: {', '.join(failed)}.",
                confidence_adjustment=-0.2,
                future_recommendations=["Review tool parameters and retry failed operations."],
            )
        if not plan.tools:
            return ReflectionRecord(
                reflection="No tools were needed for this response.",
                confidence_adjustment=0.0,
                future_recommendations=[],
            )
        return ReflectionRecord(
            reflection="All selected tools completed successfully.",
            confidence_adjustment=0.1,
            future_recommendations=["Reuse successful tool outputs in follow-up requests."],
        )
