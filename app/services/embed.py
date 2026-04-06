from __future__ import annotations

import logging
from typing import List

from app.config import get_settings
from app.services.gemini_client import GeminiApiError, GeminiClient

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self, gemini_api_key: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.embedding_provider.lower()
        self._model = self._settings.embedding_model
        self._dim = self._settings.embedding_dim

        if self._provider != "gemini":
            raise EmbeddingError(
                f"Unsupported embedding provider in Gemini-only mode: {self._provider}"
            )

        api_key = _normalize_api_key(gemini_api_key) or self._settings.gemini_api_key
        self._gemini_client: GeminiClient | None = None
        if api_key:
            self._gemini_client = GeminiClient(api_key=api_key, base_url=self._settings.gemini_base_url)
        else:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to zero-vector embeddings.")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._gemini_client is None:
            return self._zero_vectors(len(texts))
        try:
            # Note: dimension=self._dim works for text-embedding-004 models and later
            vectors = self._gemini_client.embed_documents(self._model, texts, dimension=self._dim)
        except GeminiApiError as exc:
            logger.warning("Gemini embedding failed, using fallback vectors: %s", exc)
            return self._zero_vectors(len(texts))
        return [self._fit_dimension(vector) for vector in vectors]

    def embed_query(self, query: str) -> List[float]:
        if self._gemini_client is None:
            return [0.0] * self._dim
        try:
            return self._fit_dimension(
                self._gemini_client.embed_query(self._model, query, dimension=self._dim)
            )
        except GeminiApiError as exc:
            logger.warning("Gemini query embedding failed, using fallback vector: %s", exc)
            return [0.0] * self._dim

    def _fit_dimension(self, values: List[float]) -> List[float]:
        if len(values) == self._dim:
            return values
        if len(values) > self._dim:
            return values[: self._dim]
        return values + [0.0] * (self._dim - len(values))

    def _zero_vectors(self, count: int) -> List[List[float]]:
        return [[0.0] * self._dim for _ in range(count)]


def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
