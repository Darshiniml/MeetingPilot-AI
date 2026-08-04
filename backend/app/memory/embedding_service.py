"""Local embedding service wrapper with caching, retries, and latency tracking."""

import logging
import time
from collections.abc import Sequence
from urllib.error import HTTPError, URLError

from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class CachedEmbeddingService:
    """Wrapper around app.services.embedding_service.EmbeddingService adding caching, latency measuring, and retries."""

    def __init__(self, cache_size: int = 1000) -> None:
        self._cache: dict[str, list[float]] = {}
        self._cache_size = cache_size
        self._latency_metrics: list[float] = []

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate float vector embeddings for the input texts, using local cache and retrying connection errors."""
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        # Check cache
        for idx, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                results[idx] = cached
            else:
                missing_indices.append(idx)
                missing_texts.append(text)

        # Batch request missing texts from Ollama
        if missing_texts:
            local_service = get_embedding_service()
            attempts = 3
            backoff = 0.5
            embeddings = None
            
            start_time = time.perf_counter()
            for attempt in range(1, attempts + 1):
                try:
                    embeddings = local_service.embed_texts(missing_texts)
                    break
                except (HTTPError, URLError, TimeoutError, RuntimeError) as e:
                    if attempt == attempts:
                        logger.error("Failed to generate embeddings after %d attempts: %s", attempts, e)
                        raise
                    logger.warning("Embedding attempt %d failed: %s. Retrying in %.2fs...", attempt, e, backoff)
                    time.sleep(backoff)
                    backoff *= 2

            latency = time.perf_counter() - start_time
            self._latency_metrics.append(latency)
            logger.info("Generated %d embeddings in %.2f ms", len(missing_texts), latency * 1000)

            # Store in cache and build final list
            if embeddings:
                for missing_idx, text, emb in zip(missing_indices, missing_texts, embeddings, strict=True):
                    # Evict if cache exceeds max size
                    if len(self._cache) >= self._cache_size:
                        # Pop oldest entry
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[text] = emb
                    results[missing_idx] = emb

        # Return results, filtering out any unresolved entries (should be none)
        return [r for r in results if r is not None]

    def get_average_latency_ms(self) -> float:
        """Return the average latency of embedding generation calls in milliseconds."""
        if not self._latency_metrics:
            return 0.0
        return (sum(self._latency_metrics) / len(self._latency_metrics)) * 1000

    def get_latency_count(self) -> int:
        """Return the total number of embedding generation calls tracked."""
        return len(self._latency_metrics)

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
