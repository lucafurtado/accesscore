import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by client IP, in-process only.

    Deliberately not Redis-backed: the free-tier deployment target runs a
    single instance, so there is nothing for Redis to coordinate across,
    and adding it would be an external dependency this project doesn't
    need (see redis_url's docstring in app/core/config.py). A future
    multi-instance deployment would need a shared store instead of this.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]

        while hits and hits[0] <= now - self._window_seconds:
            hits.popleft()

        if len(hits) >= self._max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        hits.append(now)
        if not hits:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


# Login is the primary brute-force target, so it gets the tighter window.
# Refresh fires automatically (silent bootstrap, 401 retry) so its limit is
# looser to avoid rate-limiting legitimate frontend usage.
_login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
_refresh_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def rate_limit_login(request: Request) -> None:
    _login_limiter.check(_client_key(request))


async def rate_limit_refresh(request: Request) -> None:
    _refresh_limiter.check(_client_key(request))


def reset_rate_limiters() -> None:
    """Test-only hook: every request in the test suite shares the same fake
    client host (ASGITransport has no real network), so without resetting
    between tests, unrelated tests would eventually collide on the same
    login/refresh budget. See tests/conftest.py."""
    _login_limiter.reset()
    _refresh_limiter.reset()
