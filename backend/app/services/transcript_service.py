"""Business logic for persisting chunk-level Whisper output."""

import logging
from datetime import datetime
from typing import Any

from app.audio.buffer import AudioChunk
from app.models.transcript import Transcript
from app.repositories.transcript_repository import TranscriptRepository
from app.transcription.models import TranscriptionResult
from app.websocket.manager import get_transcript_socket_manager
import datetime as dt
from app.vision.speaker_alignment_service import SpeakerAlignmentService
from app.vision.speaker_repository import get_speaker_repository


logger = logging.getLogger(__name__)


class TranscriptService:
    """Convert chunk-relative Whisper output into meeting transcript rows."""

    def __init__(self, transcript_repository: TranscriptRepository) -> None:
        self._transcript_repository = transcript_repository

    def persist_whisper_result(self, *, meeting_id: int, meeting_started_at: datetime, audio_chunk: AudioChunk, whisper_result: TranscriptionResult) -> list[Transcript]:
        """Store segments with timestamps relative to meeting start and stream them live."""
        alignment_service = SpeakerAlignmentService(get_speaker_repository())
        chunk_offset = (audio_chunk.started_at - meeting_started_at).total_seconds()
        
        transcripts = []
        for i, segment in enumerate(whisper_result.segments):
            start_seconds = chunk_offset + segment.start_seconds
            end_seconds = chunk_offset + segment.end_seconds
            
            abs_start = meeting_started_at + dt.timedelta(seconds=start_seconds)
            abs_end = meeting_started_at + dt.timedelta(seconds=end_seconds)
            
            speaker_id, speaker_name, speaker_conf = alignment_service.align_speaker(abs_start, abs_end)
            
            transcript = self._transcript_repository.create_transcript(
                meeting_id=meeting_id,
                chunk_index=audio_chunk.chunk_index,
                segment_index=i,
                text=segment.text,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                language=whisper_result.language,
                confidence=segment.confidence,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                speaker_confidence=speaker_conf,
            )
            transcripts.append(transcript)
            logger.info("Transcript persisted", extra={"meeting_id": meeting_id, "transcript_id": transcript.id})
            self._broadcast_transcript(meeting_id=meeting_id, transcript=transcript)
            
        return transcripts

    def _broadcast_transcript(self, *, meeting_id: int, transcript: Transcript) -> None:
        """Broadcast a newly persisted transcript chunk to connected WebSocket clients."""
        payload: dict[str, Any] = {
            "id": transcript.id,
            "meeting_id": transcript.meeting_id,
            "chunk_index": transcript.chunk_index,
            "segment_index": transcript.segment_index,
            "text": transcript.text,
            "start_seconds": transcript.start_seconds,
            "end_seconds": transcript.end_seconds,
            "language": transcript.language,
            "confidence": transcript.confidence,
            "speaker_id": transcript.speaker_id,
            "speaker_name": transcript.speaker_name,
            "speaker_confidence": transcript.speaker_confidence,
        }
        get_transcript_socket_manager().dispatch_transcript(
            meeting_id=meeting_id, transcript=payload
        )
        logger.info("WebSocket broadcast dispatched", extra={"meeting_id": meeting_id, "transcript_id": transcript.id})
