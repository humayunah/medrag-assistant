"""Tests for the provider router and circuit breaker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.router import CircuitBreaker, ProviderRouter, _retry_with_backoff
from app.providers.base import LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(name: str, *, configured: bool = True) -> MagicMock:
    """Create a mock LLMProvider with controllable behaviour."""
    provider = MagicMock()
    provider.name = name
    provider.is_configured.return_value = configured
    provider.complete = AsyncMock(
        return_value=LLMResponse(
            content="ok",
            provider=name,
            model=f"{name}-model",
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=42.0,
        )
    )
    return provider


def _make_response(provider_name: str = "test") -> LLMResponse:
    return LLMResponse(
        content="ok",
        provider=provider_name,
        model=f"{provider_name}-model",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=42.0,
    )


def _build_router(providers: list[MagicMock]) -> ProviderRouter:
    """Build a ProviderRouter wired to the given mock providers."""
    router = object.__new__(ProviderRouter)
    router._providers = providers
    router._breakers = {p.name: CircuitBreaker() for p in providers}
    return router


# ===================================================================
# CircuitBreaker tests
# ===================================================================


class TestCircuitBreaker:
    """Tests for the per-provider CircuitBreaker."""

    def test_fresh_breaker_is_not_open(self):
        cb = CircuitBreaker()
        assert cb.is_open is False

    def test_breaker_opens_after_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open is True

    def test_breaker_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False

    @patch("app.providers.router.time")
    def test_breaker_transitions_to_half_open_after_cooldown(self, mock_time):
        """After cooldown_seconds elapse the breaker reports not-open (half-open)."""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=10.0)

        # Failures happen at t=100
        mock_time.monotonic.return_value = 100.0
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Still within cooldown at t=105
        mock_time.monotonic.return_value = 105.0
        assert cb.is_open is True

        # Cooldown elapsed at t=110
        mock_time.monotonic.return_value = 110.0
        assert cb.is_open is False

    def test_record_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.is_open is False
        # Even adding one more failure should not open it.
        cb.record_failure()
        assert cb.is_open is False

    def test_multiple_successes_after_failures_keep_breaker_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_success()
        cb.record_success()
        assert cb.is_open is False
        assert cb._failure_count == 0


# ===================================================================
# _retry_with_backoff tests
# ===================================================================


class TestRetryWithBackoff:
    """Sanity checks for the retry helper."""

    @pytest.mark.asyncio
    async def test_returns_on_first_success(self):
        factory = AsyncMock(return_value=_make_response())
        result = await _retry_with_backoff(factory, max_retries=3, base_delay=0)
        assert result.content == "ok"
        assert factory.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        factory = AsyncMock(side_effect=[RuntimeError("boom"), _make_response()])
        result = await _retry_with_backoff(factory, max_retries=3, base_delay=0)
        assert result.content == "ok"
        assert factory.await_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        factory = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError, match="boom"):
            await _retry_with_backoff(factory, max_retries=3, base_delay=0)
        assert factory.await_count == 3


# ===================================================================
# ProviderRouter tests
# ===================================================================


class TestProviderRouter:
    """Tests for ProviderRouter using mock providers."""

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_first_configured_provider_is_used(self, mock_retry):
        """The first provider in the list should be tried first."""
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        expected = _make_response("alpha")
        mock_retry.return_value = expected

        result = await router.complete([{"role": "user", "content": "hi"}])

        assert result.provider == "alpha"
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_falls_back_to_next_provider_when_first_fails(self, mock_retry):
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        expected_beta = _make_response("beta")
        mock_retry.side_effect = [RuntimeError("alpha down"), expected_beta]

        result = await router.complete([{"role": "user", "content": "hi"}])

        assert result.provider == "beta"
        assert mock_retry.await_count == 2

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_skips_unconfigured_providers(self, mock_retry):
        p1 = _make_provider("alpha", configured=False)
        p2 = _make_provider("beta", configured=True)
        router = _build_router([p1, p2])

        expected = _make_response("beta")
        mock_retry.return_value = expected

        result = await router.complete([{"role": "user", "content": "hi"}])

        assert result.provider == "beta"
        # _retry_with_backoff should only have been called once (for beta).
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_skips_providers_with_open_circuit_breakers(self, mock_retry):
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        # Trip the circuit breaker for alpha.
        for _ in range(router._breakers["alpha"].failure_threshold):
            router._breakers["alpha"].record_failure()
        assert router._breakers["alpha"].is_open is True

        expected = _make_response("beta")
        mock_retry.return_value = expected

        result = await router.complete([{"role": "user", "content": "hi"}])

        assert result.provider == "beta"
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_raises_runtime_error_when_all_providers_exhausted(self, mock_retry):
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        mock_retry.side_effect = RuntimeError("provider down")

        with pytest.raises(RuntimeError, match="All LLM providers exhausted"):
            await router.complete([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_records_success_on_circuit_breaker(self, mock_retry):
        p1 = _make_provider("alpha")
        router = _build_router([p1])

        # Pre-add some failures (but below threshold).
        router._breakers["alpha"].record_failure()
        router._breakers["alpha"].record_failure()
        assert router._breakers["alpha"]._failure_count == 2

        mock_retry.return_value = _make_response("alpha")

        await router.complete([{"role": "user", "content": "hi"}])

        # Success should have reset the breaker.
        assert router._breakers["alpha"]._failure_count == 0
        assert router._breakers["alpha"].is_open is False

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_records_failure_on_circuit_breaker(self, mock_retry):
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        mock_retry.side_effect = [RuntimeError("alpha down"), _make_response("beta")]

        await router.complete([{"role": "user", "content": "hi"}])

        # Alpha should have one recorded failure.
        assert router._breakers["alpha"]._failure_count == 1

    @pytest.mark.asyncio
    @patch("app.providers.router._retry_with_backoff")
    async def test_raises_with_no_configured_providers(self, mock_retry):
        p1 = _make_provider("alpha", configured=False)
        p2 = _make_provider("beta", configured=False)
        router = _build_router([p1, p2])

        with pytest.raises(RuntimeError, match="none configured"):
            await router.complete([{"role": "user", "content": "hi"}])

        mock_retry.assert_not_awaited()

    # -- get_available_providers ----------------------------------------

    def test_get_available_providers_returns_only_configured_non_open(self):
        p1 = _make_provider("alpha", configured=True)
        p2 = _make_provider("beta", configured=False)
        p3 = _make_provider("gamma", configured=True)
        router = _build_router([p1, p2, p3])

        # Trip gamma's breaker.
        for _ in range(router._breakers["gamma"].failure_threshold):
            router._breakers["gamma"].record_failure()

        available = router.get_available_providers()

        assert available == ["alpha"]

    def test_get_available_providers_all_configured_and_healthy(self):
        p1 = _make_provider("alpha")
        p2 = _make_provider("beta")
        router = _build_router([p1, p2])

        assert router.get_available_providers() == ["alpha", "beta"]

    def test_get_available_providers_empty_when_all_down(self):
        p1 = _make_provider("alpha")
        router = _build_router([p1])

        for _ in range(router._breakers["alpha"].failure_threshold):
            router._breakers["alpha"].record_failure()

        assert router.get_available_providers() == []
