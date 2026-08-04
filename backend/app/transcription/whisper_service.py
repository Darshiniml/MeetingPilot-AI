"""Reusable local Faster-Whisper transcription service."""

import gc
import logging
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Callable

from faster_whisper import WhisperModel

from app.transcription.config import WhisperConfig
from app.transcription.models import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)


class WhisperService:
    """Load one local Whisper model and transcribe WAV chunks with it."""

    def __init__(
        self,
        config: WhisperConfig,
        model_factory: Callable[..., Any] = WhisperModel,
    ) -> None:
        """Create an unloaded service with injectable model construction for tests."""
        self._config = config
        self._model_factory = model_factory
        self._model: Any | None = None
        self._model_lock = Lock()
        self._metrics_lock = Lock()
        self._processed_chunks = 0
        self._total_processing_seconds = 0.0

    def load_model(self) -> None:
        """Load the configured model once and reuse it across every WAV chunk."""
        with self._model_lock:
            if self._model is not None:
                return
            started_at = perf_counter()
            self._model = self._model_factory(
                self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
            logger.info(
                "Faster-Whisper model loaded",
                extra={
                    "model_size": self._config.model_size,
                    "device": self._config.device,
                    "load_seconds": round(perf_counter() - started_at, 3),
                },
            )

    def warmup(self) -> None:
        """Eagerly load the model during application startup."""
        self.load_model()

    def transcribe_chunk(self, wav_path: Path | str) -> TranscriptionResult:
        """Transcribe one WAV chunk and return text, timing, and segment metadata."""
        audio_path = Path(wav_path)
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio chunk does not exist: {audio_path}")
        if audio_path.suffix.lower() != ".wav":
            raise ValueError("WhisperService accepts WAV chunk paths only")

        self.load_model()
        if self._model is None:
            raise RuntimeError("Whisper model could not be loaded")

        started_at = perf_counter()
        raw_segments, info = self._model.transcribe(
            str(audio_path),
            beam_size=self._config.beam_size,
            vad_filter=self._config.vad_filter,
        )
        segments = tuple(
            TranscriptionSegment(
                start_seconds=float(segment.start),
                end_seconds=float(segment.end),
                text=segment.text.strip(),
                confidence=getattr(segment, "avg_logprob", None),
                no_speech_probability=getattr(segment, "no_speech_prob", None),
            )
            for segment in raw_segments
        )
        processing_seconds = perf_counter() - started_at
        average_processing_seconds = self._record_processing_time(processing_seconds)
        result = TranscriptionResult(
            text=" ".join(segment.text for segment in segments if segment.text),
            language=str(info.language),
            language_probability=getattr(info, "language_probability", None),
            segments=segments,
            processing_seconds=processing_seconds,
            average_processing_seconds=average_processing_seconds,
        )
        print(f"Whisper language: {result.language}", flush=True)
        print(f"Whisper segment count: {len(result.segments)}", flush=True)
        print(f"Transcript text: {result.text}", flush=True)
        logger.info(f"Detected language: {result.language}")
        logger.info(f"Segment count: {len(result.segments)}")
        if len(result.segments) == 0:
            logger.warning(f"Whisper transcription returned 0 segments for chunk {audio_path.name} (possibly due to silence or VAD filter).")
        logger.info(f"Transcript length: {len(result.text)}")
        logger.info(
            "Audio chunk transcribed",
            extra={
                "path": str(audio_path),
                "language": result.language,
                "segments": len(result.segments),
                "processing_seconds": round(result.processing_seconds, 3),
                "average_processing_seconds": round(result.average_processing_seconds, 3),
            },
        )
        return result

    def shutdown(self) -> None:
        """Release the local model when the application stops."""
        with self._model_lock:
            self._model = None
        gc.collect()

    def _record_processing_time(self, processing_seconds: float) -> float:
        """Record one latency measurement and return the rolling average."""
        with self._metrics_lock:
            self._processed_chunks += 1
            self._total_processing_seconds += processing_seconds
            return self._total_processing_seconds / self._processed_chunks


_whisper_service: WhisperService | None = None
_whisper_service_lock = Lock()


def get_whisper_service() -> WhisperService:
    """Provide the process-wide model service for future dependency injection."""
    global _whisper_service
    with _whisper_service_lock:
        if _whisper_service is None:
            _whisper_service = WhisperService(WhisperConfig.from_environment())
        return _whisper_service
