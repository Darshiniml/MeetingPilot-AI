from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class GmailTool(BaseTool):
    def name(self) -> str: return "gmail"
    def description(self) -> str: return "Sends email through GmailProvider."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.SEND_EMAIL
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        service = self._get_service(context)
        operation = parameters.get("operation", "send_email")
        if operation == "list_sent_messages": return service.list_sent_messages()
        if operation == "send_email":
            return service.send_email(parameters["to_email"], parameters["subject"], parameters["body"], parameters.get("meeting_id", context.active_meeting), parameters.get("thread_id"))
        raise ValueError(f"Unsupported Gmail operation: {operation}")
