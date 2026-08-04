from typing import Any
from .base_tool import BaseTool
from ..context import AgentContext
from ..models import AgentIntent


class TranscriptTool(BaseTool):
    def name(self) -> str: return "transcript"
    def description(self) -> str: return "Persists transcript output through TranscriptService."
    def supports(self, intent: AgentIntent) -> bool: return intent == AgentIntent.SEARCH_TRANSCRIPT
    def execute(self, context: AgentContext, parameters: dict[str, Any]) -> Any:
        return self._get_service(context).persist_whisper_result(
            meeting_id=self._meeting_id(context, parameters),
            meeting_started_at=parameters["meeting_started_at"],
            audio_chunk=parameters["audio_chunk"],
            whisper_result=parameters["whisper_result"],
        )
