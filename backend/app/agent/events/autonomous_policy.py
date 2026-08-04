"""Rules governing autonomous event reactions and approval requirements."""

from __future__ import annotations

from dataclasses import dataclass, field

from .event_models import BaseAgentEvent
from .event_types import EventType


@dataclass(frozen=True)
class PolicyDecision:
    should_react: bool
    message: str = ""
    recommendation: str = ""
    required_approval_tools: set[str] = field(default_factory=set)


class AutonomousPolicy:
    SAFE_TOOLS = {"summary", "action_items", "transcript", "rag_chat", "meeting_history", "vision"}
    APPROVAL_REQUIRED_TOOLS = {"gmail", "calendar", "scheduler", "contacts"}

    def evaluate(self, event: BaseAgentEvent) -> PolicyDecision:
        if event.event_type == EventType.MEETING_STOPPED:
            return PolicyDecision(True, "Meeting stopped. Generate a summary and extract action items.", "Generate post-meeting summary and action items.")
        if event.event_type == EventType.TRANSCRIPT_SAVED:
            text = str(event.payload.get("text", ""))
            markers = ("by ", "will ", "follow up", "risk", "decision", "deadline")
            if any(marker in text.casefold() for marker in markers):
                return PolicyDecision(True, "Analyze the latest transcript for commitments, deadlines, decisions, and risks.", "Review transcript for follow-up work.")
            return PolicyDecision(False, recommendation="No actionable transcript signal detected.")
        if event.event_type == EventType.ACTION_ITEM_CREATED:
            return PolicyDecision(True, "Suggest a reminder for the newly created action item.", "Create a reminder after user approval.")
        if event.event_type == EventType.CALENDAR_CONFLICT:
            return PolicyDecision(True, "Suggest alternative slots for this calendar conflict.", "Present alternative meeting times; calendar changes require approval.")
        if event.event_type == EventType.MEETING_SCHEDULED:
            return PolicyDecision(True, "Suggest invitation emails for the scheduled meeting.", "Prepare invitations; sending requires approval.")
        if event.event_type in {EventType.SUMMARY_GENERATED, EventType.EMAIL_SENT}:
            return PolicyDecision(True, "Update agent memory with this completed operation.", "Record completed operation for future context.")
        return PolicyDecision(False)

    def requires_approval(self, tool_name: str) -> bool:
        return tool_name in self.APPROVAL_REQUIRED_TOOLS
