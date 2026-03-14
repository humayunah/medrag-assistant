import time
from collections import defaultdict

from starlette.requests import Request

from app.core.exceptions import RateLimitError


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window.

    Production note: Replace with Redis-backed limiter for multi-worker deployments.
    """

    def __init__(self) -> None:
        # Key: (identifier, endpoint) -> list of timestamps
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)

    def _clean_old_entries(self, key: tuple[str, str], window_seconds: int) -> None:
        now = time.time()
        cutoff = now - window_seconds
        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        key = (identifier, endpoint)
        self._clean_old_entries(key, window_seconds)

        if len(self._requests[key]) >= max_requests:
            raise RateLimitError(
                detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds}s"
            )

        self._requests[key].append(time.time())


# Singleton instance
rate_limiter = InMemoryRateLimiter()


def check_rate_limit(
    request: Request,
    endpoint: str,
    max_requests: int,
    window_seconds: int,
    use_tenant: bool = True,
) -> None:
    """Check rate limit for the current request.

    Args:
        request: The incoming request.
        endpoint: Logical endpoint name (e.g., "query", "upload").
        max_requests: Maximum requests allowed in the window.
        window_seconds: Window size in seconds.
        use_tenant: If True, rate limit per tenant. If False, per IP.
    """
    if use_tenant and hasattr(request.state, "tenant_id"):
        identifier = str(request.state.tenant_id)
    else:
        identifier = request.client.host if request.client else "unknown"

    rate_limiter.check_rate_limit(identifier, endpoint, max_requests, window_seconds)
