from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class SummaryTool(BaseTool):
    def name(self) -> str: return "summary"
    def description(self) -> str: return "Generates a summary for the active meeting."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.SUMMARIZE_MEETING
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        return self._get_service(context).generate_for_meeting(self._meeting_id(context, parameters))
