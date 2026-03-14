"""Tests for core exception hierarchy and in-memory rate limiter."""

from unittest.mock import patch

import pytest

from app.core.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from app.middleware.rate_limit import InMemoryRateLimiter


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestAppException:
    def test_defaults(self):
        exc = AppException()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.detail == "An internal error occurred"

    def test_custom_detail(self):
        exc = AppException(detail="custom message")
        assert exc.detail == "custom message"
        assert str(exc) == "custom message"


class TestNotFoundError:
    def test_defaults(self):
        exc = NotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert "not found" in exc.detail.lower()

    def test_custom_detail(self):
        exc = NotFoundError(detail="Widget #42 missing")
        assert exc.detail == "Widget #42 missing"


class TestForbiddenError:
    def test_defaults(self):
        exc = ForbiddenError()
        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"

    def test_custom_detail(self):
        exc = ForbiddenError(detail="Not allowed here")
        assert exc.detail == "Not allowed here"


class TestUnauthorizedError:
    def test_defaults(self):
        exc = UnauthorizedError()
        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"

    def test_custom_detail(self):
        exc = UnauthorizedError(detail="Token expired")
        assert exc.detail == "Token expired"


class TestConflictError:
    def test_defaults(self):
        exc = ConflictError()
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"

    def test_custom_detail(self):
        exc = ConflictError(detail="Duplicate entry")
        assert exc.detail == "Duplicate entry"


class TestValidationError:
    def test_defaults(self):
        exc = ValidationError()
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"

    def test_custom_detail(self):
        exc = ValidationError(detail="Field 'email' is required")
        assert exc.detail == "Field 'email' is required"


class TestRateLimitError:
    def test_defaults(self):
        exc = RateLimitError()
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"

    def test_custom_detail(self):
        exc = RateLimitError(detail="Slow down")
        assert exc.detail == "Slow down"


class TestServiceUnavailableError:
    def test_defaults(self):
        exc = ServiceUnavailableError()
        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"

    def test_custom_detail(self):
        exc = ServiceUnavailableError(detail="DB is down")
        assert exc.detail == "DB is down"


class TestInheritance:
    """All custom errors should be AppException subclasses."""

    @pytest.mark.parametrize(
        "cls",
        [
            NotFoundError,
            ForbiddenError,
            UnauthorizedError,
            ConflictError,
            ValidationError,
            RateLimitError,
            ServiceUnavailableError,
        ],
    )
    def test_is_subclass_of_app_exception(self, cls):
        assert issubclass(cls, AppException)


# ---------------------------------------------------------------------------
# InMemoryRateLimiter
# ---------------------------------------------------------------------------


class TestInMemoryRateLimiter:
    def test_first_request_within_limit_passes(self):
        limiter = InMemoryRateLimiter()
        # Should not raise
        limiter.check_rate_limit(
            identifier="user-1",
            endpoint="/api/query",
            max_requests=5,
            window_seconds=60,
        )

    def test_exceeding_max_requests_raises(self):
        limiter = InMemoryRateLimiter()
        for _ in range(3):
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=3, window_seconds=60
            )

        with pytest.raises(RateLimitError) as exc_info:
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=3, window_seconds=60
            )

        assert exc_info.value.status_code == 429

    def test_requests_after_window_expires_pass(self):
        limiter = InMemoryRateLimiter()

        base_time = 1000.0

        with patch("app.middleware.rate_limit.time") as mock_time:
            # Fill up the limit inside the window
            mock_time.time.return_value = base_time
            for _ in range(3):
                limiter.check_rate_limit(
                    "user-1", "/api/query", max_requests=3, window_seconds=10
                )

            # Still within window -- should be blocked
            mock_time.time.return_value = base_time + 5
            with pytest.raises(RateLimitError):
                limiter.check_rate_limit(
                    "user-1", "/api/query", max_requests=3, window_seconds=10
                )

            # Advance past the window -- old entries should be cleaned
            mock_time.time.return_value = base_time + 11
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=3, window_seconds=10
            )

    def test_different_identifiers_independent(self):
        limiter = InMemoryRateLimiter()

        # Exhaust limit for user-1
        for _ in range(2):
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=2, window_seconds=60
            )

        with pytest.raises(RateLimitError):
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=2, window_seconds=60
            )

        # user-2 should still be fine
        limiter.check_rate_limit(
            "user-2", "/api/query", max_requests=2, window_seconds=60
        )

    def test_different_endpoints_independent(self):
        limiter = InMemoryRateLimiter()

        # Exhaust limit for /api/query
        for _ in range(2):
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=2, window_seconds=60
            )

        with pytest.raises(RateLimitError):
            limiter.check_rate_limit(
                "user-1", "/api/query", max_requests=2, window_seconds=60
            )

        # Same user, different endpoint -- should be fine
        limiter.check_rate_limit(
            "user-1", "/api/upload", max_requests=2, window_seconds=60
        )
