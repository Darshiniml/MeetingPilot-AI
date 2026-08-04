from __future__ import annotations

from app.agent.events.event_models import UserMessageEvent
from app.agent.events.event_types import EventType

from .agent_context import AgentContext
from .agent_messages import AgentMessage
from .email_agent import EmailAgent
from .meeting_agent import MeetingAgent
from .memory_agent import MemoryAgent
from .research_agent import ResearchAgent
from .scheduler_agent import SchedulerAgent
from .vision_agent import VisionAgent


class AgentRegistry:
    def __init__(self, context: AgentContext, auto_register: bool = True) -> None:
        self.context = context
        self._agents = {}
        self._subscription = context.event_bus.subscribe(EventType.CHAT_MESSAGE, self._on_message)
        if auto_register:
            for agent_type in (MeetingAgent, VisionAgent, SchedulerAgent, EmailAgent, MemoryAgent, ResearchAgent):
                self.register(agent_type(context))

    def register(self, agent) -> None: self._agents[agent.name()] = agent
    def unregister(self, name: str): return self._agents.pop(name, None)
    def find_capable_agents(self, request): return [agent for agent in self._agents.values() if agent.can_handle(request)]
    def broadcast(self, message: AgentMessage, user_id: int = 0, meeting_id: int | None = None) -> None: self.context.send(message, user_id, meeting_id)
    def _on_message(self, event: UserMessageEvent) -> None:
        payload = event.payload.get("agent_message")
        if payload:
            message = AgentMessage.model_validate(payload)
            for agent in self._agents.values(): agent.receive_message(message)
