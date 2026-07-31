"""Business logic for persisting chunk-level Whisper output."""

import logging
from datetime import datetime
from typing import Any

from app.audio.buffer import AudioChunk
from app.models.transcript import Transcript
from app.repositories.transcript_repository import TranscriptRepository
from app.transcription.models import TranscriptionResult
from app.websocket.manager import get_transcript_socket_manager


logger = logging.getLogger(__name__)


class TranscriptService:
    """Convert chunk-relative Whisper output into meeting transcript rows."""

    def __init__(self, transcript_repository: TranscriptRepository) -> None:
        self._transcript_repository = transcript_repository

    def persist_whisper_result(self, *, meeting_id: int, meeting_started_at: datetime, audio_chunk: AudioChunk, whisper_result: TranscriptionResult) -> Transcript:
        """Store one result with timestamps relative to meeting start and stream it live."""
        offset = (audio_chunk.started_at - meeting_started_at).total_seconds()
        duration = audio_chunk.frame_count / audio_chunk.sample_rate
        starts = [segment.start_seconds for segment in whisper_result.segments]
        ends = [segment.end_seconds for segment in whisper_result.segments]
        scores = [segment.confidence for segment in whisper_result.segments if segment.confidence is not None]
        transcript = self._transcript_repository.create_transcript(
            meeting_id=meeting_id,
            chunk_index=audio_chunk.chunk_index,
            text=whisper_result.text,
            start_seconds=offset + (min(starts) if starts else 0.0),
            end_seconds=offset + (max(ends) if ends else duration),
            language=whisper_result.language,
            confidence=sum(scores) / len(scores) if scores else None,
        )
        logger.info("Transcript persisted", extra={"meeting_id": meeting_id, "transcript_id": transcript.id})
        self._broadcast_transcript(meeting_id=meeting_id, transcript=transcript)
        return transcript

    def _broadcast_transcript(self, *, meeting_id: int, transcript: Transcript) -> None:
        """Broadcast a newly persisted transcript chunk to connected WebSocket clients."""
        payload: dict[str, Any] = {
            "id": transcript.id,
            "meeting_id": transcript.meeting_id,
            "chunk_index": transcript.chunk_index,
            "text": transcript.text,
            "start_seconds": transcript.start_seconds,
            "end_seconds": transcript.end_seconds,
            "language": transcript.language,
            "confidence": transcript.confidence,
        }
        get_transcript_socket_manager().dispatch_transcript(
            meeting_id=meeting_id, transcript=payload
        )
        logger.info("WebSocket broadcast dispatched", extra={"meeting_id": meeting_id, "transcript_id": transcript.id})
