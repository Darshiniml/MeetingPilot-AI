from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class RAGChatTool(BaseTool):
    def name(self) -> str: return "rag_chat"
    def description(self) -> str: return "Answers meeting questions using ChatService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.GENERAL_CHAT
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        return self._get_service(context).answer_question(meeting_id=self._meeting_id(context, parameters), question=parameters.get("question", parameters.get("user_message", "")))
