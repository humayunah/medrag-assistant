"""Provider router with circuit breaker and priority-based fallback."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field

import structlog

from app.providers.base import LLMProvider, LLMResponse
from app.providers.claude import ClaudeProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.huggingface_llm import HuggingFaceProvider

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

_FAILURE_THRESHOLD = 3
_COOLDOWN_SECONDS = 60.0


@dataclass
class CircuitBreaker:
    """Per-provider circuit breaker.

    Opens after ``failure_threshold`` consecutive failures.  After
    ``cooldown_seconds`` the circuit moves to *half-open*: the next request
    is allowed through and, if it succeeds, the circuit resets.
    """

    failure_threshold: int = _FAILURE_THRESHOLD
    cooldown_seconds: float = _COOLDOWN_SECONDS
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)

    # -- State queries -----------------------------------------------------

    @property
    def is_open(self) -> bool:
        """Return *True* when the circuit is open (requests blocked)."""
        if self._failure_count < self.failure_threshold:
            return False
        # Check if cooldown has elapsed (half-open transition).
        if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
            return False
        return True

    # -- Mutation -----------------------------------------------------------

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

    def record_success(self) -> None:
        self._failure_count = 0
        self._last_failure_time = 0.0


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


async def _retry_with_backoff(
    coro_factory,
    *,
    max_retries: int = _MAX_RETRIES,
    base_delay: float = _BASE_DELAY,
) -> LLMResponse:
    """Call *coro_factory* with exponential backoff + jitter.

    ``coro_factory`` is a zero-argument callable that returns an awaitable
    producing an ``LLMResponse``.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
                logger.debug(
                    "retry.backoff",
                    attempt=attempt + 1,
                    delay_s=round(delay, 2),
                    error=str(exc),
                )
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class ProviderRouter:
    """Routes requests through a priority chain with circuit breakers.

    Priority order: **Gemini -> Groq -> HuggingFace -> Claude**.

    Features:
    - Circuit breaker per provider (3 failures -> 60 s cooldown).
    - Retry with exponential backoff (1 s, 2 s, 4 s + jitter) *within* each
      provider before moving on to the next.
    - Falls back to the next available provider on failure.
    - Logs every attempt and outcome via ``structlog``.
    """

    def __init__(self) -> None:
        self._providers: list[LLMProvider] = [
            GeminiProvider(),
            GroqProvider(),
            HuggingFaceProvider(),
            ClaudeProvider(),
        ]
        self._breakers: dict[str, CircuitBreaker] = {
            p.name: CircuitBreaker() for p in self._providers
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        """Try each provider in priority order until one succeeds.

        Raises ``RuntimeError`` only when **all** providers are exhausted.
        """
        errors: list[str] = []

        for provider in self._providers:
            breaker = self._breakers[provider.name]
            log = logger.bind(provider=provider.name)

            if not provider.is_configured():
                log.debug("provider.skipped.not_configured")
                continue

            if breaker.is_open:
                log.info("provider.skipped.circuit_open")
                continue

            try:
                response = await _retry_with_backoff(
                    lambda p=provider: p.complete(messages, **kwargs),  # type: ignore[misc]
                )
                breaker.record_success()
                log.info(
                    "provider.success",
                    model=response.model,
                    latency_ms=response.latency_ms,
                )
                return response
            except Exception as exc:
                breaker.record_failure()
                error_msg = f"{provider.name}: {exc}"
                errors.append(error_msg)
                log.warning("provider.failed", error=str(exc), exc_info=True)

        raise RuntimeError(
            f"All LLM providers exhausted. Errors: {'; '.join(errors) or 'none configured'}"
        )

    def get_available_providers(self) -> list[str]:
        """Return names of providers that are configured and not circuit-open."""
        return [
            p.name
            for p in self._providers
            if p.is_configured() and not self._breakers[p.name].is_open
        ]
