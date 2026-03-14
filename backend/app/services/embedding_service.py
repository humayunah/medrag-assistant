"""Embedding service using HuggingFace Inference API with PubMedBERT."""

from __future__ import annotations

import asyncio
from typing import Final

import httpx
import numpy as np
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_MODEL_ID: Final[str] = "NeuML/pubmedbert-base-embeddings"
_EMBEDDING_DIM: Final[int] = 768
_MAX_BATCH_SIZE: Final[int] = 32
_API_URL: Final[str] = (
    f"https://router.huggingface.co/pipeline/feature-extraction/{_MODEL_ID}"
)

_MAX_RETRIES: Final[int] = 3
_BACKOFF_BASE_S: Final[float] = 1.0
_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 503})


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize an array of vectors (row-wise)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Avoid division by zero for degenerate zero-vectors.
    norms = np.maximum(norms, 1e-12)
    return vectors / norms


class EmbeddingService:
    """Async embedding service backed by HuggingFace Inference API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {settings.HF_API_TOKEN}",
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Handles batching internally.

        Returns a list of 768-dim L2-normalized vectors.
        """
        if not texts:
            return []

        all_embeddings: list[np.ndarray] = []

        for start in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[start : start + _MAX_BATCH_SIZE]
            batch_vectors = await self._embed_batch(batch)
            all_embeddings.append(batch_vectors)

        combined = np.vstack(all_embeddings)
        normalized = _l2_normalize(combined)
        return normalized.tolist()

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string.

        Returns a 768-dim L2-normalized vector.
        """
        results = await self.embed_texts([query])
        return results[0]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _embed_batch(self, texts: list[str]) -> np.ndarray:
        """Call the HuggingFace API for a single batch with retry logic.

        Returns an (N, 768) numpy array of raw (un-normalized) embeddings.
        """
        payload = {"inputs": texts, "options": {"wait_for_model": True}}

        last_exc: BaseException | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.post(_API_URL, json=payload)

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    delay = _BACKOFF_BASE_S * (2 ** (attempt - 1))
                    logger.warning(
                        "hf_api_retryable_error",
                        status=response.status_code,
                        attempt=attempt,
                        retry_in_s=delay,
                    )
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(delay)
                        continue
                    # Final attempt — fall through to raise.
                    response.raise_for_status()

                response.raise_for_status()

                data = response.json()
                vectors = np.asarray(data, dtype=np.float32)

                if vectors.ndim == 1:
                    vectors = vectors.reshape(1, -1)

                if vectors.shape[1] != _EMBEDDING_DIM:
                    raise ValueError(
                        f"Expected {_EMBEDDING_DIM}-dim embeddings, "
                        f"got {vectors.shape[1]}"
                    )

                logger.debug(
                    "hf_embed_batch_ok",
                    batch_size=len(texts),
                    shape=vectors.shape,
                )
                return vectors

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.error(
                    "hf_api_http_error",
                    status=exc.response.status_code,
                    detail=exc.response.text[:500],
                    attempt=attempt,
                )
                # Non-retryable status — break immediately.
                if exc.response.status_code not in _RETRYABLE_STATUS_CODES:
                    break

            except httpx.TransportError as exc:
                last_exc = exc
                delay = _BACKOFF_BASE_S * (2 ** (attempt - 1))
                logger.warning(
                    "hf_api_transport_error",
                    error=str(exc),
                    attempt=attempt,
                    retry_in_s=delay,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)

        raise RuntimeError(
            f"HuggingFace embedding request failed after {_MAX_RETRIES} attempts"
        ) from last_exc

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Shut down the underlying HTTP client."""
        await self._client.aclose()
        logger.info("embedding_service_closed")
