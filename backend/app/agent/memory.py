"""Conversation and working memory maintained solely within the agent layer."""

from __future__ import annotations

from typing import Any

from .memory_models import ConversationInteraction


class ConversationMemory:
    """Bounded chronological memory of one conversation's completed interactions."""

    MAX_INTERACTIONS = 20

    def __init__(self, conversation_id: str) -> None:
        self.conversation_id = conversation_id
        self.interactions: list[ConversationInteraction] = []

    def add(self, interaction: ConversationInteraction) -> None:
        self.interactions.append(interaction)
        del self.interactions[:-self.MAX_INTERACTIONS]

    def recent(self, limit: int = 5) -> list[ConversationInteraction]:
        return self.interactions[-limit:]

    def retrieve(self, query: str, limit: int = 5) -> list[ConversationInteraction]:
        """Return lexical matches, falling back to recent conversation context."""
        terms = {term.casefold() for term in query.split() if len(term) > 2}
        matches = [
            item for item in reversed(self.interactions)
            if terms.intersection(item.user_message.casefold().split())
        ]
        return matches[:limit] or list(reversed(self.recent(limit)))


class WorkingMemory:
    """Mutable execution facts available to the reasoning engine and planner."""

    def __init__(self) -> None:
        self.shared_variables: dict[str, Any] = {}
        self.resolved_contacts: dict[str, Any] = {}
        self.calendar_events: list[Any] = []
        self.meeting_ids: list[int] = []
        self.summary_ids: list[int] = []
        self.tool_outputs: dict[str, Any] = {}

    def update_tool_output(self, tool_name: str, output: Any) -> None:
        self.tool_outputs[tool_name] = output
        if isinstance(output, dict):
            self.shared_variables.update(output)
            if tool_name == "contacts":
                self.resolved_contacts.update(output)
            if tool_name == "calendar":
                self.calendar_events.append(output)
            for key in ("meeting_id", "id"):
                if key in output and isinstance(output[key], int) and tool_name in {"scheduler", "calendar"}:
                    self.meeting_ids.append(output[key])
            if tool_name == "summary" and isinstance(output.get("id"), int):
                self.summary_ids.append(output["id"])

    def context(self) -> dict[str, Any]:
        return {
            "shared_variables": self.shared_variables,
            "resolved_contacts": self.resolved_contacts,
            "calendar_events": self.calendar_events[-3:],
            "meeting_ids": self.meeting_ids[-3:],
            "summary_ids": self.summary_ids[-3:],
            "tool_outputs": self.tool_outputs,
        }
