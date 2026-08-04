"""Centralized, environment-driven application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional .env file."""

    app_name: str = "MeetingPilot AI API"
    app_version: str = "1.0.0"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./meetingpilot.db"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 5
    whisper_vad_filter: bool = True
    whisper_load_on_startup: bool = True
    summary_llm_provider: str = "ollama"
    summary_llm_model: str = "llama3.2"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "nomic-embed-text"

    # Google OAuth Configuration
    google_client_id: str = "mock-client-id"
    google_client_secret: str = "mock-client-secret"
    google_redirect_uri: str = "http://localhost:8000/integrations/google/callback"
    google_token_encryption_key: str = "meetingpilot-default-secret-key-32b-must-change"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Return the comma-separated CORS configuration as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Create settings once per process to avoid repeated environment reads."""
    return Settings()
