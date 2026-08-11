import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import create_autospec

import pytest

from app.core.exceptions import AuthenticationError, InvalidRefreshTokenError
from app.core.security import hash_password, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


def _make_user(is_active: bool = True) -> User:
    return User(
        id=uuid.uuid4(),
        email="alice@example.com",
        hashed_password=hash_password("correct-password"),
        is_active=is_active,
    )


def _make_refresh_token(
    raw_token: str = "raw-refresh-token",
    user_id: uuid.UUID | None = None,
    revoked: bool = False,
    expires_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        token_hash=hash_refresh_token(raw_token),
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=1)),
        revoked=revoked,
    )


@pytest.fixture
def user_repo() -> Any:
    return create_autospec(UserRepository, instance=True)


@pytest.fixture
def refresh_token_repo() -> Any:
    return create_autospec(RefreshTokenRepository, instance=True)


@pytest.fixture
def audit_service() -> Any:
    return create_autospec(AuditService, instance=True)


@pytest.fixture
def service(user_repo: Any, refresh_token_repo: Any, audit_service: Any) -> AuthService:
    return AuthService(user_repo, refresh_token_repo, audit_service)


async def test_authenticate_user_succeeds_with_correct_credentials(
    service: AuthService, user_repo: Any
) -> None:
    user = _make_user()
    user_repo.get_by_email.return_value = user

    authenticated = await service.authenticate_user("alice@example.com", "correct-password")

    assert authenticated is user
    user_repo.update_last_login.assert_awaited_once_with(user)


async def test_authenticate_user_fails_with_wrong_password(
    service: AuthService, user_repo: Any
) -> None:
    user_repo.get_by_email.return_value = _make_user()

    with pytest.raises(AuthenticationError):
        await service.authenticate_user("alice@example.com", "wrong-password")


async def test_authenticate_user_fails_when_user_missing(
    service: AuthService, user_repo: Any
) -> None:
    user_repo.get_by_email.return_value = None

    with pytest.raises(AuthenticationError):
        await service.authenticate_user("nobody@example.com", "whatever")


async def test_authenticate_user_fails_when_inactive(service: AuthService, user_repo: Any) -> None:
    user_repo.get_by_email.return_value = _make_user(is_active=False)

    with pytest.raises(AuthenticationError):
        await service.authenticate_user("alice@example.com", "correct-password")


async def test_create_session_persists_refresh_token_hash_not_raw(
    service: AuthService, refresh_token_repo: Any
) -> None:
    user = _make_user()

    token_pair = await service.create_session(user)

    refresh_token_repo.create.assert_awaited_once()
    _, kwargs = refresh_token_repo.create.await_args
    assert kwargs["token_hash"] == hash_refresh_token(token_pair.refresh_token)
    assert kwargs["token_hash"] != token_pair.refresh_token


async def test_refresh_session_rotates_token(
    service: AuthService, user_repo: Any, refresh_token_repo: Any
) -> None:
    user = _make_user()
    raw_token = "raw-refresh-token"
    record = _make_refresh_token(raw_token, user_id=user.id)
    refresh_token_repo.get_by_token_hash.return_value = record
    user_repo.get_by_id.return_value = user

    new_pair = await service.refresh_session(raw_token)

    refresh_token_repo.revoke.assert_awaited_once_with(record)
    assert new_pair.refresh_token != raw_token
    refresh_token_repo.create.assert_awaited_once()


async def test_refresh_session_fails_for_unknown_token(
    service: AuthService, refresh_token_repo: Any
) -> None:
    refresh_token_repo.get_by_token_hash.return_value = None

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session("unknown-token")


async def test_refresh_session_fails_for_revoked_token(
    service: AuthService, refresh_token_repo: Any
) -> None:
    refresh_token_repo.get_by_token_hash.return_value = _make_refresh_token(revoked=True)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session("revoked-token")


async def test_refresh_session_fails_for_expired_token(
    service: AuthService, refresh_token_repo: Any
) -> None:
    refresh_token_repo.get_by_token_hash.return_value = _make_refresh_token(
        expires_at=datetime.now(UTC) - timedelta(days=1)
    )

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session("expired-token")


async def test_refresh_session_fails_for_inactive_user(
    service: AuthService, user_repo: Any, refresh_token_repo: Any
) -> None:
    user = _make_user(is_active=False)
    refresh_token_repo.get_by_token_hash.return_value = _make_refresh_token(user_id=user.id)
    user_repo.get_by_id.return_value = user

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session("token-for-inactive-user")


async def test_logout_revokes_token(service: AuthService, refresh_token_repo: Any) -> None:
    record = _make_refresh_token()
    refresh_token_repo.get_by_token_hash.return_value = record

    await service.logout("some-token")

    refresh_token_repo.revoke.assert_awaited_once_with(record)


async def test_logout_fails_for_unknown_token(
    service: AuthService, refresh_token_repo: Any
) -> None:
    refresh_token_repo.get_by_token_hash.return_value = None

    with pytest.raises(InvalidRefreshTokenError):
        await service.logout("unknown-token")


async def test_logout_fails_for_already_revoked_token(
    service: AuthService, refresh_token_repo: Any
) -> None:
    refresh_token_repo.get_by_token_hash.return_value = _make_refresh_token(revoked=True)

    with pytest.raises(InvalidRefreshTokenError):
        await service.logout("already-revoked-token")


async def test_change_password_updates_hash_and_revokes_sessions(
    service: AuthService, user_repo: Any, refresh_token_repo: Any
) -> None:
    user = _make_user()

    await service.change_password(user, "correct-password", "new-strong-password")

    user_repo.update_password.assert_awaited_once()
    refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(user.id)


async def test_change_password_fails_with_wrong_current_password(service: AuthService) -> None:
    user = _make_user()

    with pytest.raises(AuthenticationError):
        await service.change_password(user, "wrong-password", "new-strong-password")
