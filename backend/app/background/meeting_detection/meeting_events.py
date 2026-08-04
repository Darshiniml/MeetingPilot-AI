from __future__ import annotations

import logging
from app.agent.events.event_types import EventType
from app.agent.events.event_models import BaseAgentEvent

logger = logging.getLogger(__name__)

# Register Phase 10.2 event types dynamically into EventType Enum
def extend_meeting_event_types() -> None:
    additional_members = {
        "MEETING_DETECTED": "meeting_detected",
        "MEETING_LOST": "meeting_lost",
    }
    for name, value in additional_members.items():
        if name not in EventType.__members__:
            member = str.__new__(EventType, value)
            member._name_ = name
            member._value_ = value
            EventType._member_map_[name] = member
            EventType._value2member_map_[value] = member
            EventType._member_names_.append(name)
            logger.debug("[Meeting Detection] Registered extended EventType: %s -> %s", name, value)

extend_meeting_event_types()

class MeetingDetectedEvent(BaseAgentEvent):
    event_type: EventType = EventType.MEETING_DETECTED

class MeetingLostEvent(BaseAgentEvent):
    event_type: EventType = EventType.MEETING_LOST
