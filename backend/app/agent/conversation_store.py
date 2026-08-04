"""In-memory conversation-memory repository for the agent layer."""

from __future__ import annotations

from .memory import ConversationMemory, WorkingMemory


class ConversationStore:
    """Keeps independent conversation and working memory by conversation id."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationMemory] = {}
        self._working_memories: dict[str, WorkingMemory] = {}

    def get_conversation(self, conversation_id: str) -> ConversationMemory:
        return self._conversations.setdefault(conversation_id, ConversationMemory(conversation_id))

    def get_working_memory(self, conversation_id: str) -> WorkingMemory:
        return self._working_memories.setdefault(conversation_id, WorkingMemory())

    def retrieve(self, conversation_id: str, query: str, limit: int = 5):
        return self.get_conversation(conversation_id).retrieve(query, limit)
