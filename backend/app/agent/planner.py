"""LLM-backed strict-JSON planning for the autonomous agent."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any

from .exceptions import PlannerException
from .models import AgentIntent, ExecutionPlan
from .planner_response_parser import PlannerResponseParser
from .prompt_templates import build_planner_prompt, build_repair_prompt

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.ai.providers import LLMProvider


class Planner:
    """Uses the configured Ollama-backed provider to create validated plans."""

    def __init__(self, provider: "LLMProvider | None" = None, parser: PlannerResponseParser | None = None) -> None:
        self._provider: Any = provider or self._default_provider()
        self._parser = parser or PlannerResponseParser()

    def plan(self, user_message: str, memory_context: dict | None = None) -> ExecutionPlan:
        """Generate a strict JSON plan, repairing one malformed response if needed."""
        if not isinstance(user_message, str) or not user_message.strip():
            raise PlannerException("A non-empty user message is required to create a plan.")

        started_at = perf_counter()
        logger.info("LLM planner context size=%d", len(str(memory_context or {})))
        provider_result = self._provider.generate(build_planner_prompt(user_message, memory_context))
        raw_response = provider_result.content
        logger.info(
            "LLM planner completed in %.2f ms; tokens=%s; response=%s",
            (perf_counter() - started_at) * 1000,
            getattr(provider_result, "tokens", None),
            raw_response,
        )
        try:
            plan = self._parser.parse(raw_response)
        except PlannerException:
            logger.warning("LLM planner JSON invalid; requesting one repair")
            repaired_result = self._provider.generate(build_repair_prompt(raw_response))
            repaired_response = repaired_result.content
            logger.info("LLM planner repair response=%s", repaired_response)
            try:
                plan = self._parser.parse(repaired_response)
            except PlannerException:
                logger.warning("LLM planner repair failed; using general-chat fallback")
                return self._fallback(user_message)
        if plan.confidence < 0.6:
            logger.info("LLM planner confidence %.2f below threshold; using general-chat fallback", plan.confidence)
            return self._fallback(user_message)
        return plan

    @staticmethod
    def _fallback(user_message: str) -> ExecutionPlan:
        return ExecutionPlan(
            intent=AgentIntent.GENERAL_CHAT,
            confidence=0.0,
            tools=["rag_chat"],
            reasoning="LLM planning was unavailable, invalid, or below the confidence threshold.",
            parameters={"user_message": user_message},
        )

    @staticmethod
    def _default_provider() -> "LLMProvider":
        """Lazily obtain the existing configured Ollama provider."""
        from app.ai.providers import get_llm_provider

        return get_llm_provider()
