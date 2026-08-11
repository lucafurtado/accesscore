from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def _create_user(
    db_session: AsyncSession, email: str, password: str = "correct-password"
) -> User:
    repo = UserRepository(db_session)
    return await repo.create(email=email, hashed_password=hash_password(password))


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


async def test_change_password_success_flow(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _create_user(db_session, "change-pw@example.com")
    tokens = await _login(client, user.email, "correct-password")
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "new-strong-password"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204

    old_password_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "new-strong-password"}
    )
    assert new_password_login.status_code == 200

    refresh_after_change = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after_change.status_code == 401


async def test_change_password_wrong_current_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "wrong-current@example.com")
    tokens = await _login(client, user.email, "correct-password")

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "totally-wrong", "new_password": "new-strong-password"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 401


async def test_change_password_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "whatever", "new_password": "new-strong-password"},
    )

    assert response.status_code == 401


async def test_change_password_invalid_new_password_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "short-pw@example.com")
    tokens = await _login(client, user.email, "correct-password")

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "short"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 422
