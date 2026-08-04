from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class ActionItemTool(BaseTool):
    def name(self) -> str: return "action_items"
    def description(self) -> str: return "Extracts action items using ActionItemService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.LIST_ACTION_ITEMS
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        return self._get_service(context).extract_for_meeting(self._meeting_id(context, parameters))
