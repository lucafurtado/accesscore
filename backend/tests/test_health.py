from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient


async def test_health_check_reports_ok_when_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "accesscore-api"
    assert body["database"] == "up"
    assert "X-Request-ID" in response.headers


class _BrokenEngine:
    """Stands in for app.main.engine when the database is unreachable.

    AsyncEngine.connect is a read-only attribute, so it can't be patched
    directly; swapping the whole `engine` name in app.main's namespace for
    this fake is the simplest way to simulate a connection failure.
    """

    def connect(self) -> Any:
        @asynccontextmanager
        async def _cm() -> Any:
            raise ConnectionError("simulated database outage")
            yield  # pragma: no cover - unreachable, keeps this an async generator

        return _cm()


async def test_health_check_reports_503_when_database_is_unreachable(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.engine", _BrokenEngine())

    response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "down"
