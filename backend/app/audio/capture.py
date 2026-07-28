"""Native PCM audio capture wrapper."""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class AudioCaptureConfig:
    """PCM capture settings shared by microphone and loopback sources."""

    sample_rate: int = 16_000
    channels: int = 1
    frame_duration_ms: int = 100

    @property
    def frame_count(self) -> int:
        """Return the number of samples in one short capture frame."""
        return self.sample_rate * self.frame_duration_ms // 1_000


class AudioCapture:
    """Own one active native recorder and expose short PCM frame reads."""

    def __init__(self, device: Any, config: AudioCaptureConfig) -> None:
        """Initialize capture for a selected SoundCard recording device."""
        self._device = device
        self._config = config
        self._recorder_context: Any | None = None
        self._recorder: Any | None = None

    def start(self) -> None:
        """Open the native recorder before the background worker starts."""
        if self._recorder is not None:
            raise RuntimeError("Audio capture is already running")
        self._recorder_context = self._device.recorder(
            samplerate=self._config.sample_rate,
            channels=self._config.channels,
            blocksize=self._config.frame_count,
        )
        self._recorder = self._recorder_context.__enter__()

    def read_frame(self) -> np.ndarray:
        """Read one short PCM frame as normalized floating-point samples."""
        if self._recorder is None:
            raise RuntimeError("Audio capture has not been started")
        return np.asarray(
            self._recorder.record(numframes=self._config.frame_count),
            dtype=np.float32,
        )

    def stop(self) -> None:
        """Release the native recorder and its operating-system device handle."""
        if self._recorder_context is not None:
            self._recorder_context.__exit__(None, None, None)
        self._recorder_context = None
        self._recorder = None
