import uuid
from typing import Any
from unittest.mock import create_autospec

import pytest

from app.core.exceptions import AlreadyExistsError, PrivilegeEscalationError
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.user_service import UserService

ACTOR_ID = uuid.uuid4()


def _make_user(email: str = "user@example.com") -> User:
    return User(id=uuid.uuid4(), email=email, hashed_password="hashed")


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
def service(user_repo: Any, refresh_token_repo: Any, audit_service: Any) -> UserService:
    return UserService(user_repo, refresh_token_repo, audit_service)


# --- create_user ---


async def test_create_user_succeeds_when_email_available(
    service: UserService, user_repo: Any, audit_service: Any
) -> None:
    user_repo.get_by_email.return_value = None
    user_repo.create.return_value = _make_user("new@example.com")

    result = await service.create_user(
        "New@Example.com", "password123", "New User", actor_user_id=ACTOR_ID
    )

    assert result.email == "new@example.com"
    user_repo.create.assert_awaited_once()
    audit_service.record.assert_awaited_once()
    _, kwargs = audit_service.record.await_args
    assert kwargs["action"] == "user.created"
    assert kwargs["context"] == {"email": "new@example.com"}


async def test_create_user_fails_when_email_taken(service: UserService, user_repo: Any) -> None:
    user_repo.get_by_email.return_value = _make_user("taken@example.com")

    with pytest.raises(AlreadyExistsError):
        await service.create_user("taken@example.com", "password123", None, actor_user_id=ACTOR_ID)

    user_repo.create.assert_not_awaited()


# --- update_user ---


async def test_update_user_changes_full_name(
    service: UserService, user_repo: Any, audit_service: Any
) -> None:
    user = _make_user()
    user_repo.update_profile.return_value = user

    await service.update_user(user, full_name="Updated Name", actor_user_id=ACTOR_ID)

    user_repo.update_profile.assert_awaited_once_with(user, full_name="Updated Name", email=None)
    audit_service.record.assert_awaited_once()
    _, kwargs = audit_service.record.await_args
    assert kwargs["context"] == {"changed_fields": ["full_name"]}


async def test_update_user_with_no_changes_does_not_audit(
    service: UserService, user_repo: Any, audit_service: Any
) -> None:
    user = _make_user()
    user_repo.update_profile.return_value = user

    await service.update_user(user, actor_user_id=ACTOR_ID)

    audit_service.record.assert_not_awaited()


async def test_update_user_email_fails_when_taken_by_another_user(
    service: UserService, user_repo: Any
) -> None:
    user = _make_user("original@example.com")
    user_repo.get_by_email.return_value = _make_user("taken@example.com")

    with pytest.raises(AlreadyExistsError):
        await service.update_user(user, email="taken@example.com", actor_user_id=ACTOR_ID)

    user_repo.update_profile.assert_not_awaited()


async def test_update_user_email_unchanged_skips_duplicate_check(
    service: UserService, user_repo: Any
) -> None:
    user = _make_user("same@example.com")
    user_repo.update_profile.return_value = user

    await service.update_user(user, email="same@example.com", actor_user_id=ACTOR_ID)

    user_repo.get_by_email.assert_not_awaited()


# --- disable_user / reactivate_user ---


async def test_disable_user_succeeds_for_different_users(
    service: UserService, user_repo: Any, refresh_token_repo: Any, audit_service: Any
) -> None:
    acting_user = _make_user("admin@example.com")
    target_user = _make_user("target@example.com")

    await service.disable_user(acting_user, target_user)

    user_repo.set_active.assert_awaited_once_with(target_user, False)
    refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(target_user.id)
    audit_service.record.assert_awaited_once()
    _, kwargs = audit_service.record.await_args
    assert kwargs["action"] == "user.disabled"


async def test_disable_user_blocks_self_disable(service: UserService, user_repo: Any) -> None:
    user = _make_user()

    with pytest.raises(PrivilegeEscalationError):
        await service.disable_user(user, user)

    user_repo.set_active.assert_not_awaited()


async def test_reactivate_user_delegates_to_repository(
    service: UserService, user_repo: Any, audit_service: Any
) -> None:
    acting_user = _make_user("admin@example.com")
    target_user = _make_user("target@example.com")

    await service.reactivate_user(acting_user, target_user)

    user_repo.set_active.assert_awaited_once_with(target_user, True)
    audit_service.record.assert_awaited_once()
    _, kwargs = audit_service.record.await_args
    assert kwargs["action"] == "user.reactivated"


# --- list_users / get_stats ---


async def test_list_users_delegates_to_repository(service: UserService, user_repo: Any) -> None:
    user_repo.list_paginated.return_value = ([], None, False)

    result = await service.list_users(cursor=None, limit=20)

    assert result == ([], None, False)
    user_repo.list_paginated.assert_awaited_once_with(cursor=None, limit=20, is_active=None, q=None)


async def test_get_stats_combines_total_and_active_counts(
    service: UserService, user_repo: Any
) -> None:
    user_repo.count.side_effect = [5, 3]

    stats = await service.get_stats()

    assert stats.total == 5
    assert stats.active == 3
