from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class CalendarTool(BaseTool):
    def name(self) -> str: return "calendar"
    def description(self) -> str: return "Uses GoogleCalendarProvider for calendar operations."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.GOOGLE_CALENDAR
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        service = self._get_service(context)
        operation = parameters.get("operation", "list_events")
        if operation == "list_events": return service.list_events()
        if operation == "create_event": return service.create_event(parameters["details"])
        if operation == "check_availability": return service.check_availability(parameters["details"])
        raise ValueError(f"Unsupported calendar operation: {operation}")
