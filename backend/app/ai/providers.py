"""Small provider abstraction for text-generation models."""

from dataclasses import dataclass
import json
from typing import Protocol
from urllib.request import Request, urlopen

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class LLMResult:
    """Normalized output from any text-generation provider."""

    content: str


class LLMProvider(Protocol):
    """Contract implemented by swappable text-generation providers."""

    def generate(self, prompt: str) -> LLMResult:
        """Generate text for a fully constructed prompt."""


class OllamaProvider:
    """Ollama's local HTTP generation API adapter."""

    def __init__(self, *, base_url: str, model: str) -> None:
        self._url = f"{base_url.rstrip('/')}/api/generate"
        self._model = model

    def generate(self, prompt: str) -> LLMResult:
        request = Request(
            self._url,
            data=json.dumps({"model": self._model, "prompt": prompt, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode())
        content = str(payload.get("response", "")).strip()
        if not content:
            raise RuntimeError("Configured LLM provider returned an empty summary")
        return LLMResult(content=content)


def get_llm_provider() -> LLMProvider:
    """Construct the configured provider without coupling services to it."""
    settings = get_settings()
    if settings.summary_llm_provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.summary_llm_model,
        )
    raise ValueError(f"Unsupported summary LLM provider: {settings.summary_llm_provider}")
