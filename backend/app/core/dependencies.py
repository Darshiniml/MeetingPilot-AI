"""Application dependency composition for HTTP request handling."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.session import SessionLocal
from app.audio.audio_service import AudioService, get_audio_service
from app.audio.buffer import AudioChunk
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.summary_repository import SummaryRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.services.meeting_service import MeetingService
from app.services.transcript_service import TranscriptService
from app.services.summary_service import SummaryService
from app.ai.providers import get_llm_provider
from app.transcription.pipeline import TranscriptPersistencePipeline
from app.transcription.whisper_service import WhisperService, get_whisper_service


DatabaseSession = Annotated[Session, Depends(get_db)]


def build_chunk_processor(
    *, meeting_id: int, meeting_started_at: datetime, whisper_service: WhisperService
) -> Callable[[AudioChunk], None]:
    """Build a worker-safe processor with a fresh database session per chunk."""
    def process(audio_chunk: AudioChunk) -> None:
        with SessionLocal() as session:
            pipeline = TranscriptPersistencePipeline(
                meeting_id=meeting_id,
                meeting_started_at=meeting_started_at,
                whisper_service=whisper_service,
                transcript_service=TranscriptService(TranscriptRepository(session)),
            )
            pipeline.handle_audio_chunk(audio_chunk)

    return process


def get_meeting_service(session: DatabaseSession) -> MeetingService:
    """Build a request-scoped MeetingService with its repository dependency."""
    return MeetingService(
        MeetingRepository(session),
        audio_service=get_audio_service(),
        whisper_service=get_whisper_service(),
        chunk_processor_factory=build_chunk_processor,
        summary_service=SummaryService(
            TranscriptRepository(session),
            SummaryRepository(session),
            get_llm_provider(),
        ),
    )
