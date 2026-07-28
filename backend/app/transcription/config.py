"""Configuration for local Faster-Whisper inference."""

from dataclasses import dataclass

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class WhisperConfig:
    """Immutable inference settings for one local Whisper model instance."""

    model_size: str
    device: str
    compute_type: str
    beam_size: int
    vad_filter: bool

    @classmethod
    def from_environment(cls) -> "WhisperConfig":
        """Build inference configuration from the centralized application settings."""
        settings = get_settings()
        return cls(
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            beam_size=settings.whisper_beam_size,
            vad_filter=settings.whisper_vad_filter,
        )
