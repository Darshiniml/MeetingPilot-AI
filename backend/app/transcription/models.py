"""Typed transcription result contracts independent of database persistence."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    """A text span with timestamps relative to its source WAV chunk."""

    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None
    no_speech_probability: float | None


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Complete transcription output for one audio chunk."""

    text: str
    language: str
    language_probability: float | None
    segments: tuple[TranscriptionSegment, ...]
    processing_seconds: float
    average_processing_seconds: float
