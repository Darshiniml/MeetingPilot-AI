from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class MeetingHistoryTool(BaseTool):
    def name(self) -> str: return "meeting_history"
    def description(self) -> str: return "Retrieves meeting history using MeetingHistoryService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.SEARCH_HISTORY
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        service = self._get_service(context)
        if parameters.get("action") == "list":
            return service.list_meetings(offset=int(parameters.get("offset", 0)), limit=int(parameters.get("limit", 20)))
        return service.get_meeting(self._meeting_id(context, parameters))
