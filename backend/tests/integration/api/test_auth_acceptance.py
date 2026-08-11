"""Milestone 1 acceptance suite: end-to-end authentication flows and security invariants.

Each group of tests below corresponds to one scenario (A-H) from the Milestone 1 spec.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
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


# --- Scenario A: Login -------------------------------------------------------


async def test_scenario_a_login_issues_valid_token_pair(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-a@example.com")

    tokens = await _login(client, user.email, "correct-password")

    assert "access_token" in tokens
    assert "refresh_token" in tokens

    payload = jwt.decode(
        tokens["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == str(user.id)


# --- Scenario B: Invalid login ------------------------------------------------


async def test_scenario_b_invalid_login_cases_all_return_401_with_same_message(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    active_user = await _create_user(db_session, "scenario-b-active@example.com")
    inactive_user = await _create_user(
        db_session, "scenario-b-inactive@example.com", is_active=False
    )

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": active_user.email, "password": "wrong-password"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody-scenario-b@example.com", "password": "whatever"},
    )
    inactive = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user.email, "password": "correct-password"},
    )

    for response in (wrong_password, unknown_email, inactive):
        assert response.status_code == 401

    # Identical detail message across all three cases: no signal that
    # distinguishes "wrong password" from "unknown email" from "inactive
    # account" -- this is what prevents account enumeration.
    messages = {r.json()["detail"] for r in (wrong_password, unknown_email, inactive)}
    assert len(messages) == 1


# --- Scenario C: Refresh rotation --------------------------------------------


async def test_scenario_c_refresh_rotation(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _create_user(db_session, "scenario-c@example.com")
    tokens = await _login(client, user.email, "correct-password")
    r1 = tokens["refresh_token"]

    refresh_1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert refresh_1.status_code == 200
    r2 = refresh_1.json()["refresh_token"]

    reuse_r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert reuse_r1.status_code == 401

    refresh_2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    assert refresh_2.status_code == 200


# --- Scenario D: Logout -------------------------------------------------------


async def test_scenario_d_logout_invalidates_refresh_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-d@example.com")
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


# --- Scenario E: Password change ----------------------------------------------


async def test_scenario_e_password_change_invalidates_sessions_and_old_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-e@example.com")
    tokens = await _login(client, user.email, "correct-password")

    change_response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "brand-new-password"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert change_response.status_code == 204

    refresh_after_change = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_after_change.status_code == 401

    old_password_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "brand-new-password"}
    )
    assert new_password_login.status_code == 200


# --- Scenario F: Access token validation ---------------------------------------
# There is no generic "/me" endpoint in Milestone 1, so PUT /change-password
# (the only Bearer-protected route so far) is used as the HTTP-layer proxy for
# exercising get_current_user. Each invalid-token case supplies a syntactically
# valid request body so the ONLY variable under test is the token itself --
# the dependency rejects it before the route body (and its current_password
# check) ever runs.


async def test_scenario_f_valid_token_authenticates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-f-valid@example.com")
    tokens = await _login(client, user.email, "correct-password")

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "another-new-password"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 204


async def test_scenario_f_expired_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-f-expired@example.com")
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now - timedelta(minutes=30),
            "exp": now - timedelta(minutes=15),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "irrelevant-new-pass"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


async def test_scenario_f_malformed_token_returns_401(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "irrelevant-new-pass"},
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401


async def test_scenario_f_modified_signature_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-f-tampered@example.com")
    token = create_access_token(user.id)
    tampered_token = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "irrelevant-new-pass"},
        headers={"Authorization": f"Bearer {tampered_token}"},
    )

    assert response.status_code == 401


async def test_scenario_f_nonexistent_user_returns_401(client: AsyncClient) -> None:
    token = create_access_token(uuid.uuid4())

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "irrelevant-new-pass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


async def test_scenario_f_inactive_user_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-f-inactive@example.com", is_active=False)
    token = create_access_token(user.id)

    response = await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-password", "new_password": "irrelevant-new-pass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


# --- Scenario G: Persistence safety --------------------------------------------


async def test_scenario_g_password_and_refresh_token_never_stored_in_plaintext(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    plaintext_password = "never-store-this-plaintext"
    user = await _create_user(db_session, "scenario-g@example.com", password=plaintext_password)

    tokens = await _login(client, user.email, plaintext_password)
    raw_refresh_token = tokens["refresh_token"]

    assert user.hashed_password != plaintext_password
    assert plaintext_password not in user.hashed_password

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    stored_tokens = result.scalars().all()
    assert len(stored_tokens) >= 1
    for stored in stored_tokens:
        assert stored.token_hash != raw_refresh_token
        assert raw_refresh_token not in stored.token_hash


# --- Scenario H: Sensitive data -------------------------------------------------


async def test_scenario_h_password_not_logged(
    client: AsyncClient, db_session: AsyncSession, capsys: Any
) -> None:
    distinctive_password = "super-secret-do-not-log-xyz123"
    user = await _create_user(
        db_session, "scenario-h-pw@example.com", password=distinctive_password
    )
    capsys.readouterr()  # discard setup noise before the call under test

    await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": distinctive_password}
    )

    captured = capsys.readouterr()
    assert distinctive_password not in captured.out
    assert distinctive_password not in captured.err


async def test_scenario_h_refresh_token_not_logged(
    client: AsyncClient, db_session: AsyncSession, capsys: Any
) -> None:
    user = await _create_user(db_session, "scenario-h-rt@example.com")
    tokens = await _login(client, user.email, "correct-password")
    capsys.readouterr()  # discard login output before the call under test

    await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    captured = capsys.readouterr()
    assert tokens["refresh_token"] not in captured.out
    assert tokens["refresh_token"] not in captured.err


async def test_scenario_h_hashed_password_never_in_api_responses(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, "scenario-h-response@example.com")

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    assert "hashed_password" not in login_response.text
    assert user.hashed_password not in login_response.text
