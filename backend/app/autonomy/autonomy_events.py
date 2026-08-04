from __future__ import annotations

import logging
from app.agent.events.event_types import EventType
from app.agent.events.event_models import BaseAgentEvent

logger = logging.getLogger(__name__)

# Register Phase 10.4 event types dynamically inside EventType Enum at runtime
def extend_autonomy_event_types() -> None:
    additional_members = {
        "REASONING_CYCLE_COMPLETED": "reasoning_cycle_completed",
        "DECISION_MADE": "decision_made",
        "ACTION_EXECUTED": "action_executed",
        "APPROVAL_REQUIRED": "approval_required",
        "APPROVAL_APPROVED": "approval_approved",
        "APPROVAL_REJECTED": "approval_rejected",
    }
    for name, value in additional_members.items():
        if name not in EventType.__members__:
            member = str.__new__(EventType, value)
            member._name_ = name
            member._value_ = value
            EventType._member_map_[name] = member
            EventType._value2member_map_[value] = member
            EventType._member_names_.append(name)
            logger.debug("[Autonomy Engine] Registered extended EventType: %s -> %s", name, value)

extend_autonomy_event_types()

class ReasoningCycleCompletedEvent(BaseAgentEvent):
    event_type: EventType = EventType.REASONING_CYCLE_COMPLETED

class DecisionMadeEvent(BaseAgentEvent):
    event_type: EventType = EventType.DECISION_MADE

class ActionExecutedEvent(BaseAgentEvent):
    event_type: EventType = EventType.ACTION_EXECUTED

class ApprovalRequiredEvent(BaseAgentEvent):
    event_type: EventType = EventType.APPROVAL_REQUIRED

class ApprovalApprovedEvent(BaseAgentEvent):
    event_type: EventType = EventType.APPROVAL_APPROVED

class ApprovalRejectedEvent(BaseAgentEvent):
    event_type: EventType = EventType.APPROVAL_REJECTED
