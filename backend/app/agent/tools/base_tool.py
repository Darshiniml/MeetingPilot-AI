"""Base contract for all agent tool adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ..context import AgentContext
from ..models import AgentIntent

ServiceFactory = Callable[[AgentContext], Any]


class BaseTool(ABC):
    """Adapter base that resolves an existing service without owning its logic."""

    def __init__(self, service: Any = None, service_factory: ServiceFactory | None = None) -> None:
        self._service = service
        self._service_factory = service_factory

    @abstractmethod
    def name(self) -> str:
        """Return the stable registry name for this tool."""

    @abstractmethod
    def description(self) -> str:
        """Describe the capability exposed by this adapter."""

    @abstractmethod
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        """Delegate one request to the underlying existing capability."""

    @abstractmethod
    def supports(self, intent: AgentIntent) -> bool:
        """Return whether this tool is selected for an intent."""

    def _get_service(self, context: AgentContext) -> Any:
        if self._service_factory is not None:
            return self._service_factory(context)
        if self._service is not None:
            return self._service
        raise RuntimeError(f"{self.name()} requires an injected service or service factory.")

    @staticmethod
    def _meeting_id(context: AgentContext, parameters: dict[str, Any]) -> int:
        meeting_id = parameters.get("meeting_id", context.active_meeting)
        if meeting_id is None:
            raise ValueError("A meeting_id is required for this tool.")
        return int(meeting_id)
