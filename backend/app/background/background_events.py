from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import Field

from app.agent.events.event_types import EventType
from app.agent.events.event_models import BaseAgentEvent

logger = logging.getLogger(__name__)

# Register additional event types dynamically into EventType Enum at runtime
def extend_event_types() -> None:
    additional_members = {
        "AGENT_STARTED": "agent_started",
        "AGENT_STOPPED": "agent_stopped",
        "AGENT_PAUSED": "agent_paused",
        "AGENT_RESUMED": "agent_resumed",
        "HEALTH_CHANGED": "health_changed",
        "RECORDING_STARTED": "recording_started",
        "RECORDING_STOPPED": "recording_stopped",
    }
    
    # We alter EventType's internal dict mappings dynamically
    for name, value in additional_members.items():
        if name not in EventType.__members__:
            member = str.__new__(EventType, value)
            member._name_ = name
            member._value_ = value
            EventType._member_map_[name] = member
            EventType._value2member_map_[value] = member
            EventType._member_names_.append(name)
            logger.debug("Registered extended EventType: %s -> %s", name, value)

# Call dynamic extension immediately
extend_event_types()

# Event model classes using BaseAgentEvent
class AgentStartedEvent(BaseAgentEvent):
    event_type: EventType = EventType.AGENT_STARTED

class AgentStoppedEvent(BaseAgentEvent):
    event_type: EventType = EventType.AGENT_STOPPED

class AgentPausedEvent(BaseAgentEvent):
    event_type: EventType = EventType.AGENT_PAUSED

class AgentResumedEvent(BaseAgentEvent):
    event_type: EventType = EventType.AGENT_RESUMED

class HealthChangedEvent(BaseAgentEvent):
    event_type: EventType = EventType.HEALTH_CHANGED

class RecordingStartedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RECORDING_STARTED

class RecordingStoppedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RECORDING_STOPPED
