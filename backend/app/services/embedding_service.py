"""Local Ollama embedding client for transcript and question vectors."""

import json
from collections.abc import Sequence
from urllib.request import Request, urlopen

from app.config.settings import get_settings


class EmbeddingService:
    """Generate batches of embeddings through the local Ollama server."""

    def __init__(self, *, base_url: str, model: str) -> None:
        self._url = f"{base_url.rstrip('/')}/api/embed"
        self._model = model

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one float vector per input string, preserving input order."""
        if not texts:
            return []
        request = Request(
            self._url,
            data=json.dumps({"model": self._model, "input": list(texts)}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode())
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise RuntimeError("Ollama returned an invalid embedding response")
        vectors = [[float(value) for value in embedding] for embedding in embeddings]
        if any(not vector for vector in vectors):
            raise RuntimeError("Ollama returned an empty embedding")
        return vectors


def get_embedding_service() -> EmbeddingService:
    """Build the configured, fully local embedding service."""
    settings = get_settings()
    return EmbeddingService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )
