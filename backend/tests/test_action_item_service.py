"""Unit tests for AI action-item extraction."""

import unittest
from dataclasses import dataclass

from app.ai.providers import LLMResult
from app.services.action_item_service import ActionItemService


@dataclass
class TranscriptChunk:
    text: str


class FakeTranscriptRepository:
    def list_transcripts_for_meeting(self, _meeting_id: int):
        return [TranscriptChunk("Ana will publish the report by 2026-08-15."), TranscriptChunk("  ")]


class FakeActionItemRepository:
    def __init__(self) -> None:
        self.meeting_id: int | None = None
        self.items = []

    def replace_for_meeting(self, *, meeting_id: int, items):
        self.meeting_id = meeting_id
        self.items = list(items)
        return self.items


class FakeProvider:
    def __init__(self, content: str) -> None:
        self.content = content
        self.prompt = ""

    def generate(self, prompt: str) -> LLMResult:
        self.prompt = prompt
        return LLMResult(content=self.content)


class ActionItemServiceTests(unittest.TestCase):
    def test_extracts_and_normalizes_ollama_json(self) -> None:
        repository = FakeActionItemRepository()
        provider = FakeProvider(
            '[{"task":"Publish report","owner":"Ana","due_date":"2026-08-15","priority":"High","status":"Pending"}]'
        )
        service = ActionItemService(FakeTranscriptRepository(), repository, provider)

        result = service.extract_for_meeting(42)

        self.assertEqual(repository.meeting_id, 42)
        self.assertIn("JSON array only", provider.prompt)
        self.assertEqual(result[0].task, "Publish report")
        self.assertEqual(result[0].owner, "Ana")
        self.assertEqual(result[0].priority, "High")
        self.assertFalse(result[0].is_completed)
        self.assertEqual(result[0].due_at.date().isoformat(), "2026-08-15")

    def test_allows_null_metadata_and_ignores_missing_task(self) -> None:
        repository = FakeActionItemRepository()
        provider = FakeProvider(
            '[{"task":"Follow up","owner":null,"due_date":"not-a-date","priority":null,"status":"Pending"}, {"task":null,"owner":null,"due_date":null,"priority":null,"status":"Pending"}]'
        )
        service = ActionItemService(FakeTranscriptRepository(), repository, provider)

        result = service.extract_for_meeting(7)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].owner)
        self.assertIsNone(result[0].due_at)
        self.assertIsNone(result[0].priority)
