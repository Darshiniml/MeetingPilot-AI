"""Bounded PCM buffering and temporary WAV chunk persistence."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4
import wave

import numpy as np

from app.audio.devices import AudioSource


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """A temporary WAV file produced from one contiguous capture interval."""

    path: Path
    source: AudioSource
    sample_rate: int
    frame_count: int
    chunk_index: int
    started_at: datetime
    created_at: datetime


class AudioChunkBuffer:
    """Accumulate short PCM frames until a target chunk duration is reached."""

    def __init__(self, *, sample_rate: int, channels: int, chunk_duration_seconds: int = 10) -> None:
        """Create an empty buffer configured for fixed-duration output chunks."""
        self._target_frames = sample_rate * chunk_duration_seconds
        self._channels = channels
        self._pending = np.empty((0, channels), dtype=np.float32)

    def append(self, frame: np.ndarray) -> list[np.ndarray]:
        """Append one frame and return each completed fixed-duration chunk."""
        normalized_frame = self._normalize(frame)
        self._pending = np.concatenate((self._pending, normalized_frame), axis=0)
        completed: list[np.ndarray] = []
        while len(self._pending) >= self._target_frames:
            completed.append(self._pending[: self._target_frames])
            self._pending = self._pending[self._target_frames :]
        return completed

    def drain(self) -> np.ndarray | None:
        """Return a final partial chunk when capture stops, if samples remain."""
        if len(self._pending) == 0:
            return None
        remaining = self._pending
        self._pending = np.empty((0, self._channels), dtype=np.float32)
        return remaining

    def _normalize(self, frame: np.ndarray) -> np.ndarray:
        """Normalize recorder output to the configured two-dimensional PCM shape."""
        if frame.ndim == 1:
            frame = frame.reshape((-1, 1))
        if frame.ndim != 2 or frame.shape[1] != self._channels:
            raise ValueError("Captured frame does not match the configured channel count")
        return frame


class TemporaryWavChunkWriter:
    """Write normalized PCM chunks to temporary, session-scoped WAV files."""

    def __init__(self, root_directory: Path | None = None) -> None:
        """Create a writable temporary directory for one recording session."""
        base_directory = root_directory or Path(gettempdir()) / "meetingpilot" / "audio"
        self._session_directory = base_directory / uuid4().hex
        self._session_directory.mkdir(parents=True, exist_ok=True)
        self._chunk_number = 0

    def write(
        self,
        samples: np.ndarray,
        *,
        source: AudioSource,
        sample_rate: int,
        started_at: datetime | None = None,
    ) -> AudioChunk:
        """Persist one PCM chunk as lossless 16-bit WAV audio."""
        normalized = samples.reshape((-1, 1)) if samples.ndim == 1 else samples
        pcm_samples = np.clip(normalized, -1.0, 1.0)
        pcm_samples = (pcm_samples * 32_767).astype("<i2")
        created_at = datetime.now(timezone.utc)
        chunk_index = self._chunk_number
        path = self._session_directory / (
            f"{source.value}_{chunk_index:05d}_{created_at:%Y%m%dT%H%M%SZ}.wav"
        )
        self._chunk_number += 1
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(pcm_samples.shape[1])
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_samples.tobytes())
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Chunk written")
        logger.info(f"Chunk path: {path}")
        logger.info(f"Chunk duration: {len(pcm_samples) / sample_rate}s")
        logger.info(f"Chunk index: {chunk_index}")
        
        max_amplitude = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
        rms_amplitude = float(np.sqrt(np.mean(samples**2))) if len(samples) > 0 else 0.0
        duration = len(pcm_samples) / sample_rate
        size_bytes = pcm_samples.nbytes
        print("Chunk written", flush=True)
        print(f"Chunk path: {path}", flush=True)
        print(f"Chunk index: {chunk_index}", flush=True)
        print(f"Chunk duration: {duration}s", flush=True)
        print(f"Chunk size: {size_bytes} bytes", flush=True)
        print(f"Audio RMS: {rms_amplitude:.6f}", flush=True)
        print(f"Maximum amplitude: {max_amplitude:.6f}", flush=True)
        return AudioChunk(
            path=path,
            source=source,
            sample_rate=sample_rate,
            frame_count=len(pcm_samples),
            chunk_index=chunk_index,
            started_at=started_at or created_at,
            created_at=created_at,
        )
