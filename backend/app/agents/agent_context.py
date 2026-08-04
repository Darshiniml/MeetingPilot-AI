from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from app.agent.conversation_store import ConversationStore
from app.agent.events.event_bus import EventBus
from app.agent.events.event_models import UserMessageEvent
from app.agent.reasoning_engine import ReasoningEngine
from app.agent.registry import ToolRegistry

from .agent_messages import AgentMessage


@dataclass
class MultiAgentMetrics:
    agent_invocations: int = 0
    execution_time_ms: float = 0.0
    coordination_latency_ms: float = 0.0
    tool_usage: int = 0
    handoffs: int = 0
    successes: int = 0
    failures: int = 0


@dataclass
class AgentContext:
    """Single shared state surface supplied to every specialized agent."""
    tool_registry: ToolRegistry
    reasoning_engine: ReasoningEngine
    conversation_store: ConversationStore = field(default_factory=ConversationStore)
    event_bus: EventBus = field(default_factory=EventBus)
    metrics: MultiAgentMetrics = field(default_factory=MultiAgentMetrics)
    event_history: list[AgentMessage] = field(default_factory=list)

    def send(self, message: AgentMessage, user_id: int = 0, meeting_id: int | None = None) -> None:
        self.event_history.append(message)
        self.metrics.handoffs += 1
        self.event_bus.publish(UserMessageEvent(user_id=user_id, meeting_id=meeting_id, payload={"agent_message": message.model_dump(mode="json")}))
