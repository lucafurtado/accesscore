import uuid
from typing import Any
from unittest.mock import create_autospec

import pytest

from app.core.exceptions import AlreadyExistsError, PrivilegeEscalationError
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.rbac_service import RBACService


def _make_user() -> User:
    return User(id=uuid.uuid4(), email="user@example.com", hashed_password="hashed")


def _make_role(name: str = "Manager") -> Role:
    return Role(id=uuid.uuid4(), name=name)


def _make_permission(resource: str = "users", action: str = "read") -> Permission:
    return Permission(id=uuid.uuid4(), resource=resource, action=action)


@pytest.fixture
def permission_repo() -> Any:
    return create_autospec(PermissionRepository, instance=True)


@pytest.fixture
def role_repo() -> Any:
    return create_autospec(RoleRepository, instance=True)


@pytest.fixture
def user_repo() -> Any:
    return create_autospec(UserRepository, instance=True)


@pytest.fixture
def service(permission_repo: Any, role_repo: Any, user_repo: Any) -> RBACService:
    return RBACService(permission_repo, role_repo, user_repo)


# --- has_permission ---


async def test_has_permission_true_when_in_effective_set(
    service: RBACService, role_repo: Any
) -> None:
    user = _make_user()
    role_repo.get_user_effective_permissions.return_value = {"users:read", "users:update"}

    assert await service.has_permission(user, "users:read") is True


async def test_has_permission_false_when_not_in_effective_set(
    service: RBACService, role_repo: Any
) -> None:
    user = _make_user()
    role_repo.get_user_effective_permissions.return_value = {"users:read"}

    assert await service.has_permission(user, "users:disable") is False


# --- Permission management ---


async def test_create_permission_succeeds_when_new(
    service: RBACService, permission_repo: Any
) -> None:
    permission_repo.exists.return_value = False
    permission_repo.create.return_value = _make_permission()

    result = await service.create_permission("users", "read")

    assert result.resource == "users"
    permission_repo.create.assert_awaited_once_with("users", "read", None)


async def test_create_permission_fails_when_already_exists(
    service: RBACService, permission_repo: Any
) -> None:
    permission_repo.exists.return_value = True

    with pytest.raises(AlreadyExistsError):
        await service.create_permission("users", "read")

    permission_repo.create.assert_not_awaited()


async def test_list_permissions_delegates_to_repository(
    service: RBACService, permission_repo: Any
) -> None:
    permissions = [_make_permission("users", "read"), _make_permission("users", "create")]
    permission_repo.list_all.return_value = permissions

    result = await service.list_permissions()

    assert result == permissions


async def test_delete_permission_delegates_to_repository(
    service: RBACService, permission_repo: Any
) -> None:
    permission = _make_permission()

    await service.delete_permission(permission)

    permission_repo.delete.assert_awaited_once_with(permission)


# --- Role management ---


async def test_create_role_succeeds_when_name_available(
    service: RBACService, role_repo: Any
) -> None:
    role_repo.get_by_name.return_value = None
    role_repo.create.return_value = _make_role("Manager")

    result = await service.create_role("Manager", "Manages users")

    assert result.name == "Manager"
    role_repo.create.assert_awaited_once_with("Manager", "Manages users")


async def test_create_role_fails_when_name_taken(service: RBACService, role_repo: Any) -> None:
    role_repo.get_by_name.return_value = _make_role("Manager")

    with pytest.raises(AlreadyExistsError):
        await service.create_role("Manager")

    role_repo.create.assert_not_awaited()


async def test_update_role_keeping_same_name_skips_duplicate_check(
    service: RBACService, role_repo: Any
) -> None:
    role = _make_role("Manager")
    role_repo.update.return_value = role

    await service.update_role(role, name="Manager", description="Updated")

    role_repo.get_by_name.assert_not_awaited()
    role_repo.update.assert_awaited_once_with(role, name="Manager", description="Updated")


async def test_update_role_renaming_to_available_name_succeeds(
    service: RBACService, role_repo: Any
) -> None:
    role = _make_role("OldName")
    role_repo.get_by_name.return_value = None
    role_repo.update.return_value = role

    await service.update_role(role, name="NewName")

    role_repo.update.assert_awaited_once_with(role, name="NewName", description=None)


async def test_update_role_renaming_to_taken_name_fails(
    service: RBACService, role_repo: Any
) -> None:
    role = _make_role("OldName")
    role_repo.get_by_name.return_value = _make_role("TakenName")

    with pytest.raises(AlreadyExistsError):
        await service.update_role(role, name="TakenName")

    role_repo.update.assert_not_awaited()


async def test_delete_role_delegates_to_repository(service: RBACService, role_repo: Any) -> None:
    role = _make_role()

    await service.delete_role(role)

    role_repo.delete.assert_awaited_once_with(role)


async def test_list_roles_delegates_to_repository(service: RBACService, role_repo: Any) -> None:
    roles = [_make_role("Admin"), _make_role("Analyst")]
    role_repo.list_all.return_value = roles

    result = await service.list_roles()

    assert result == roles


async def test_assign_permission_to_role_delegates_to_repository(
    service: RBACService, role_repo: Any
) -> None:
    role = _make_role()
    permission = _make_permission()

    await service.assign_permission_to_role(role, permission)

    role_repo.assign_permission.assert_awaited_once_with(role, permission)


async def test_remove_permission_from_role_delegates_to_repository(
    service: RBACService, role_repo: Any
) -> None:
    role = _make_role()
    permission = _make_permission()

    await service.remove_permission_from_role(role, permission)

    role_repo.remove_permission.assert_awaited_once_with(role, permission)


# --- User-role management / privilege escalation ---


async def test_assign_role_to_user_succeeds_for_different_users(
    service: RBACService, role_repo: Any
) -> None:
    acting_user = _make_user()
    target_user = _make_user()
    role = _make_role()

    await service.assign_role_to_user(acting_user, target_user, role)

    role_repo.assign_role_to_user.assert_awaited_once_with(target_user, role)


async def test_assign_role_to_user_blocks_self_assignment(
    service: RBACService, role_repo: Any
) -> None:
    user = _make_user()
    role = _make_role()

    with pytest.raises(PrivilegeEscalationError):
        await service.assign_role_to_user(user, user, role)

    role_repo.assign_role_to_user.assert_not_awaited()


async def test_remove_role_from_user_delegates_to_repository(
    service: RBACService, role_repo: Any
) -> None:
    acting_user = _make_user()
    target_user = _make_user()
    role = _make_role()

    await service.remove_role_from_user(acting_user, target_user, role)

    role_repo.remove_role_from_user.assert_awaited_once_with(target_user, role)


async def test_list_user_roles_delegates_to_repository(
    service: RBACService, role_repo: Any
) -> None:
    user = _make_user()
    roles = [_make_role("Admin")]
    role_repo.list_user_roles.return_value = roles

    result = await service.list_user_roles(user)

    assert result == roles
