from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, hash_refresh_token
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


async def _create_user(
    db_session: AsyncSession,
    email: str,
    password: str = "correct-password",
    is_active: bool = True,
) -> User:
    repo = UserRepository(db_session)
    user = await repo.create(email=email, hashed_password=hash_password(password))
    if not is_active:
        user.is_active = False
        await db_session.flush()
    return user


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


async def test_refresh_rotates_token_and_invalidates_old_one(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="rotate@example.com")
    tokens = await _login(client, user.email, "correct-password")
    r1 = tokens["refresh_token"]

    refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert refresh_response.status_code == 200
    r2 = refresh_response.json()["refresh_token"]
    assert r2 != r1

    reuse_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert reuse_response.status_code == 401

    second_refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    assert second_refresh_response.status_code == 200


async def test_refresh_with_unknown_token_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "does-not-exist"})

    assert response.status_code == 401


async def test_refresh_with_expired_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="expired-refresh@example.com")
    raw_token = "expired-raw-token"
    repo = RefreshTokenRepository(db_session)
    await repo.create(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})

    assert response.status_code == 401


async def test_refresh_with_revoked_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="revoked-refresh@example.com")
    raw_token = "revoked-raw-token"
    repo = RefreshTokenRepository(db_session)
    record = await repo.create(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await repo.revoke(record)

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})

    assert response.status_code == 401


async def test_refresh_with_inactive_user_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="inactive-refresh@example.com", is_active=False)
    raw_token = "inactive-user-raw-token"
    repo = RefreshTokenRepository(db_session)
    await repo.create(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})

    assert response.status_code == 401


async def test_logout_revokes_token_and_subsequent_refresh_fails(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="logout-user@example.com")
    tokens = await _login(client, user.email, "correct-password")
    refresh_token = tokens["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after_logout.status_code == 401


async def test_logout_with_unknown_token_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout", json={"refresh_token": "does-not-exist"})

    assert response.status_code == 401


async def test_logout_with_already_revoked_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="double-logout@example.com")
    tokens = await _login(client, user.email, "correct-password")
    refresh_token = tokens["refresh_token"]

    first_logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert first_logout.status_code == 204

    second_logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert second_logout.status_code == 401
