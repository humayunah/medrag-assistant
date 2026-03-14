"""Anthropic Claude provider using the ``anthropic`` SDK."""

from __future__ import annotations

import time

import structlog
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.providers.base import LLMProvider, LLMResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _extract_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Separate the system message from the conversation messages.

    Anthropic expects ``system`` as a top-level parameter, not inside the
    messages list.

    Returns:
        ``(system_text, remaining_messages)``
    """
    system_text: str | None = None
    remaining: list[dict] = []

    for msg in messages:
        if msg.get("role") == "system":
            system_text = msg.get("content", "")
        else:
            remaining.append(msg)

    return system_text, remaining


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    name: str = "claude"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model_name = model
        self._client: AsyncAnthropic | None = None
        if self.is_configured():
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if self._client is None:
            raise RuntimeError(
                "ClaudeProvider is not configured (missing ANTHROPIC_API_KEY)"
            )

        log = logger.bind(provider=self.name, model=self._model_name)
        log.debug(
            "claude.complete.start", temperature=temperature, max_tokens=max_tokens
        )

        system_text, conversation = _extract_system(messages)

        kwargs: dict = {
            "model": self._model_name,
            "messages": conversation,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        start = time.monotonic()
        response = await self._client.messages.create(**kwargs)
        latency_ms = (time.monotonic() - start) * 1_000

        # Anthropic returns a list of content blocks; concatenate text blocks.
        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )

        prompt_tokens = response.usage.input_tokens or 0
        completion_tokens = response.usage.output_tokens or 0

        log.info(
            "claude.complete.done",
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
            response = await self._client.messages.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            logger.warning("claude.health_check.failed", exc_info=True)
            return False
