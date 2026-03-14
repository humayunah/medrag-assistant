"""Groq provider using the ``groq`` SDK (OpenAI-compatible)."""

from __future__ import annotations

import time

import structlog
from groq import AsyncGroq

from app.core.config import settings
from app.providers.base import LLMProvider, LLMResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(LLMProvider):
    """Groq cloud provider -- OpenAI-compatible chat completions."""

    name: str = "groq"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model_name = model
        self._client: AsyncGroq | None = None
        if self.is_configured():
            self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if self._client is None:
            raise RuntimeError("GroqProvider is not configured (missing GROQ_API_KEY)")

        log = logger.bind(provider=self.name, model=self._model_name)
        log.debug("groq.complete.start", temperature=temperature, max_tokens=max_tokens)

        start = time.monotonic()
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,  # type: ignore[arg-type]  # OpenAI-format passthrough
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.monotonic() - start) * 1_000

        choice = response.choices[0]
        content = choice.message.content or ""

        prompt_tokens = 0
        completion_tokens = 0
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens or 0
            completion_tokens = response.usage.completion_tokens or 0

        log.info(
            "groq.complete.done",
            latency_ms=round(latency_ms, 1),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 1),
        )

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            response = await self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            logger.warning("groq.health_check.failed", exc_info=True)
            return False
