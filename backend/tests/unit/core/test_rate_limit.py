import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter


class TestInMemoryRateLimiter:
    def test_allows_requests_under_the_limit(self) -> None:
        limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.check("client-a")

    def test_blocks_requests_once_the_limit_is_reached(self) -> None:
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        limiter.check("client-a")
        limiter.check("client-a")

        with pytest.raises(HTTPException) as exc_info:
            limiter.check("client-a")

        assert exc_info.value.status_code == 429

    def test_keys_are_tracked_independently(self) -> None:
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        limiter.check("client-a")
        limiter.check("client-b")  # different key, must not raise

        with pytest.raises(HTTPException):
            limiter.check("client-a")

    def test_requests_are_allowed_again_once_the_window_has_elapsed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=10)
        current_time = 1_000.0
        monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: current_time)

        limiter.check("client-a")
        with pytest.raises(HTTPException):
            limiter.check("client-a")

        current_time += 11
        monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: current_time)
        limiter.check("client-a")  # window elapsed, must not raise
