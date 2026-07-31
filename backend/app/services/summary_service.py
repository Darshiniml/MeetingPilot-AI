"""Business logic for generating and persisting one meeting summary."""

from dataclasses import dataclass

from app.ai.providers import LLMProvider
from app.models.summary import Summary
from app.repositories.summary_repository import SummaryRepository
from app.repositories.transcript_repository import TranscriptRepository


@dataclass(frozen=True, slots=True)
class GeneratedSummary:
    """Structured result returned by the summary use case."""

    content: str


class SummaryService:
    """Build prompts and coordinate summary generation without database leakage."""

    def __init__(
        self,
        transcript_repository: TranscriptRepository,
        summary_repository: SummaryRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._transcript_repository = transcript_repository
        self._summary_repository = summary_repository
        self._llm_provider = llm_provider

    def generate_for_meeting(self, meeting_id: int) -> Summary | None:
        """Summarize all non-empty transcript chunks in chronological order."""
        transcript = "\n".join(
            chunk.text.strip()
            for chunk in self._transcript_repository.list_transcripts_for_meeting(meeting_id)
            if chunk.text.strip()
        )
        if not transcript:
            return None
        generated = GeneratedSummary(content=self._llm_provider.generate(self._build_prompt(transcript)).content)
        return self._summary_repository.upsert_for_meeting(
            meeting_id=meeting_id,
            content=generated.content,
        )

    def get_for_meeting(self, meeting_id: int) -> Summary | None:
        """Return a previously generated meeting summary."""
        return self._summary_repository.get_for_meeting(meeting_id)

    @staticmethod
    def _build_prompt(transcript: str) -> str:
        return (
            "Create a concise, accurate meeting summary from the transcript below. "
            "Use the headings: Overview, Key Decisions, Discussion Points, and Next Steps. "
            "Do not invent facts.\n\nTranscript:\n"
            f"{transcript}"
        )
