"""AI action-item extraction business logic."""

import json
from datetime import date, datetime, time, timezone
from typing import Any

from app.ai.providers import LLMProvider
from app.models.action_item import ActionItem
from app.repositories.action_item_repository import ActionItemDraft, ActionItemRepository
from app.repositories.transcript_repository import TranscriptRepository


class ActionItemPromptBuilder:
    """Build the provider prompt for strict action-item JSON extraction."""

    @staticmethod
    def build(transcript: str) -> str:
        return (
            "Extract only explicit meeting action items from the transcript. "
            "Return a JSON array only, with no Markdown or explanation. Each item must "
            "have exactly these fields: task, owner, due_date, priority, status. "
            "Use null when task metadata is unavailable. status must be 'Pending'. "
            "due_date must be an ISO-8601 date or null.\n\nTranscript:\n"
            f"{transcript}"
        )


class ActionItemService:
    """Extract, validate, and persist action items for a completed meeting."""

    def __init__(
        self,
        transcript_repository: TranscriptRepository,
        action_item_repository: ActionItemRepository,
        llm_provider: LLMProvider,
        prompt_builder: ActionItemPromptBuilder | None = None,
    ) -> None:
        self._transcript_repository = transcript_repository
        self._action_item_repository = action_item_repository
        self._llm_provider = llm_provider
        self._prompt_builder = prompt_builder or ActionItemPromptBuilder()

    def extract_for_meeting(self, meeting_id: int) -> list[ActionItem]:
        """Extract and replace one meeting's action items from ordered transcript text."""
        transcript = "\n".join(
            chunk.text.strip()
            for chunk in self._transcript_repository.list_transcripts_for_meeting(meeting_id)
            if chunk.text.strip()
        )
        if not transcript:
            return self._action_item_repository.replace_for_meeting(
                meeting_id=meeting_id, items=[]
            )
        response = self._llm_provider.generate(self._prompt_builder.build(transcript))
        drafts = self._parse_response(response.content)
        return self._action_item_repository.replace_for_meeting(
            meeting_id=meeting_id, items=drafts
        )

    @classmethod
    def _parse_response(cls, response: str) -> list[ActionItemDraft]:
        payload = cls._load_json_array(response)
        drafts: list[ActionItemDraft] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Action item response must contain JSON objects")
            task = cls._nullable_string(item.get("task"))
            if task is None:
                continue
            drafts.append(
                ActionItemDraft(
                    task=task,
                    owner=cls._nullable_string(item.get("owner")),
                    due_at=cls._parse_due_date(item.get("due_date")),
                    priority=cls._nullable_string(item.get("priority")),
                    is_completed=cls._nullable_string(item.get("status")) == "Completed",
                )
            )
        return drafts

    @staticmethod
    def _load_json_array(response: str) -> list[Any]:
        content = response.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise ValueError("Action item response must be a JSON array")
        return payload

    @staticmethod
    def _nullable_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _parse_due_date(value: Any) -> datetime | None:
        text = ActionItemService._nullable_string(value)
        if text is None:
            return None
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            return None
        return datetime.combine(parsed, time.min, tzinfo=timezone.utc)
