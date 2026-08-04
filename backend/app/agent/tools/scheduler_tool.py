from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class SchedulerTool(BaseTool):
    def name(self) -> str: return "scheduler"
    def description(self) -> str: return "Plans meetings through SchedulerService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.SCHEDULE_MEETING
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        request_text = parameters.get("request_text", parameters.get("user_message", ""))
        return self._get_service(context).plan_meeting(request_text, user_id=context.current_user)
