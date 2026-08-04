from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class VisionTool(BaseTool):
    def name(self) -> str: return "vision"
    def description(self) -> str: return "Inspects the meeting display using VisionService."
    def supports(self, intent: AgentIntent) -> bool: return False
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        return self._get_service(context).inspect_once()
