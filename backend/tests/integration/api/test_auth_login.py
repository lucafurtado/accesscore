from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def _create_user(
    db_session: AsyncSession,
    email: str = "login-user@example.com",
    password: str = "correct-password",
    is_active: bool = True,
) -> User:
    repo = UserRepository(db_session)
    user = await repo.create(
        email=email, hashed_password=hash_password(password), full_name="Test User"
    )
    if not is_active:
        user.is_active = False
        await db_session.flush()
    return user


async def test_login_success_returns_token_pair(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session)
    assert user.last_login_at is None

    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60

    payload = jwt.decode(
        body["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == str(user.id)

    await db_session.refresh(user)
    assert user.last_login_at is not None


async def test_login_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="wrong-pw@example.com")

    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    assert response.status_code == 401


async def test_login_inactive_user_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="inactive-login@example.com", is_active=False)

    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    assert response.status_code == 401


async def test_login_persists_refresh_token_as_hash_not_raw(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="hash-check@example.com")

    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    raw_refresh_token = response.json()["refresh_token"]

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    stored = result.scalar_one()

    assert stored.token_hash != raw_refresh_token
    assert len(stored.token_hash) == 64


async def test_login_is_rate_limited_per_client(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, email="rate-limited@example.com")

    # The limiter allows 10 requests/minute; wrong-password attempts still
    # count against the budget (rate limiting must not trust the payload).
    for _ in range(10):
        response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    assert blocked.status_code == 429
