from __future__ import annotations

import logging
from app.agent.events.event_types import EventType
from app.agent.events.event_models import BaseAgentEvent

logger = logging.getLogger(__name__)

# Register additional event types dynamically inside EventType Enum at runtime
def extend_recording_event_types() -> None:
    additional_members = {
        "RECORDING_PAUSED": "recording_paused",
        "RECORDING_RESUMED": "recording_resumed",
        "PIPELINE_STARTED": "pipeline_started",
        "PIPELINE_COMPLETED": "pipeline_completed",
        "SESSION_CREATED": "session_created",
        "SESSION_CLOSED": "session_closed",
    }
    for name, value in additional_members.items():
        if name not in EventType.__members__:
            member = str.__new__(EventType, value)
            member._name_ = name
            member._value_ = value
            EventType._member_map_[name] = member
            EventType._value2member_map_[value] = member
            EventType._member_names_.append(name)
            logger.debug("[Recording Pipeline] Registered extended EventType: %s -> %s", name, value)

extend_recording_event_types()

from app.background.background_events import RecordingStartedEvent, RecordingStoppedEvent

class RecordingPausedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RECORDING_PAUSED

class RecordingResumedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RECORDING_RESUMED

class PipelineStartedEvent(BaseAgentEvent):
    event_type: EventType = EventType.PIPELINE_STARTED

class PipelineCompletedEvent(BaseAgentEvent):
    event_type: EventType = EventType.PIPELINE_COMPLETED

class SessionCreatedEvent(BaseAgentEvent):
    event_type: EventType = EventType.SESSION_CREATED

class SessionClosedEvent(BaseAgentEvent):
    event_type: EventType = EventType.SESSION_CLOSED
