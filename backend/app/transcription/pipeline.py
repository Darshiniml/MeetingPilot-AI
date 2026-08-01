"""Audio-to-Whisper-to-database orchestration for one active meeting."""

from datetime import datetime
import logging

from app.audio.buffer import AudioChunk
from app.models.transcript import Transcript
from app.services.transcript_service import TranscriptService
from app.transcription.whisper_service import WhisperService


logger = logging.getLogger(__name__)


class TranscriptPersistencePipeline:
    """Transcribe each emitted chunk and persist its transcript row."""

    def __init__(self, *, meeting_id: int, meeting_started_at: datetime, whisper_service: WhisperService, transcript_service: TranscriptService) -> None:
        self._meeting_id = meeting_id
        self._meeting_started_at = meeting_started_at
        self._whisper_service = whisper_service
        self._transcript_service = transcript_service

    def handle_audio_chunk(self, audio_chunk: AudioChunk) -> list[Transcript]:
        """Transcribe and persist one completed WAV chunk."""
        logger.info("Whisper started", extra={"path": str(audio_chunk.path), "chunk_index": audio_chunk.chunk_index})
        result = self._whisper_service.transcribe_chunk(audio_chunk.path)
        logger.info("Transcript generated", extra={"chunk_index": audio_chunk.chunk_index, "text_length": len(result.text)})
        return self._transcript_service.persist_whisper_result(meeting_id=self._meeting_id, meeting_started_at=self._meeting_started_at, audio_chunk=audio_chunk, whisper_result=result)
