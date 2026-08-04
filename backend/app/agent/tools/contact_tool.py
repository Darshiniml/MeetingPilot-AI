from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class ContactTool(BaseTool):
    def name(self) -> str: return "contacts"
    def description(self) -> str: return "Searches contacts through ContactService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.CONTACT_SEARCH
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        query = parameters.get("query", parameters.get("user_message", ""))
        return self._get_service(context).search_contacts(query, limit=int(parameters.get("limit", 10)))
