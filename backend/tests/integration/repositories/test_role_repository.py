import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


async def test_create_and_get_by_id(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)

    created = await repo.create(name="Manager", description="Manages users")
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.name == "Manager"
    assert fetched.description == "Manages users"


async def test_get_by_id_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


async def test_get_by_name(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)
    created = await repo.create(name="Analyst")

    fetched = await repo.get_by_name("Analyst")

    assert fetched is not None
    assert fetched.id == created.id


async def test_get_by_name_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)

    result = await repo.get_by_name("DoesNotExist")

    assert result is None


async def test_list_all_returns_roles_ordered_by_name(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)
    await repo.create(name="Zebra")
    await repo.create(name="Alpha")

    roles = await repo.list_all()
    names = [r.name for r in roles]

    assert names == sorted(names)
    assert "Zebra" in names
    assert "Alpha" in names


async def test_update_role(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)
    role = await repo.create(name="Temp", description="Old description")

    updated = await repo.update(role, description="New description")

    assert updated.name == "Temp"
    assert updated.description == "New description"


async def test_delete_role(db_session: AsyncSession) -> None:
    repo = RoleRepository(db_session)
    role = await repo.create(name="Deletable")

    await repo.delete(role)

    assert await repo.get_by_id(role.id) is None


async def test_assign_and_remove_permission(db_session: AsyncSession) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    role = await role_repo.create(name="RoleWithPerm")
    permission = await permission_repo.create(resource="users", action="read")

    await role_repo.assign_permission(role, permission)
    await db_session.refresh(role, attribute_names=["permissions"])
    assert permission in role.permissions

    await role_repo.remove_permission(role, permission)
    await db_session.refresh(role, attribute_names=["permissions"])
    assert permission not in role.permissions


async def test_list_permissions_returns_assigned_permissions(db_session: AsyncSession) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    role = await role_repo.create(name="RoleForListing")
    read_perm = await permission_repo.create(resource="widgets", action="read")
    update_perm = await permission_repo.create(resource="widgets", action="update")

    await role_repo.assign_permission(role, read_perm)
    await role_repo.assign_permission(role, update_perm)

    permissions = await role_repo.list_permissions(role)

    assert {p.id for p in permissions} == {read_perm.id, update_perm.id}


async def test_list_permissions_empty_for_role_without_permissions(
    db_session: AsyncSession,
) -> None:
    role_repo = RoleRepository(db_session)
    role = await role_repo.create(name="BarePermissionsRole")

    permissions = await role_repo.list_permissions(role)

    assert permissions == []


async def test_assign_permission_is_idempotent(db_session: AsyncSession) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    role = await role_repo.create(name="IdempotentRole")
    permission = await permission_repo.create(resource="users", action="create")

    await role_repo.assign_permission(role, permission)
    await role_repo.assign_permission(role, permission)

    await db_session.refresh(role, attribute_names=["permissions"])
    assert len(role.permissions) == 1


async def test_assign_and_remove_role_to_user(db_session: AsyncSession) -> None:
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.create(email="rolecheck@example.com", hashed_password=hash_password("x"))
    role = await role_repo.create(name="UserRole")

    await role_repo.assign_role_to_user(user, role)
    roles = await role_repo.list_user_roles(user)
    assert any(r.id == role.id for r in roles)

    await role_repo.remove_role_from_user(user, role)
    roles = await role_repo.list_user_roles(user)
    assert not any(r.id == role.id for r in roles)


async def test_get_user_effective_permissions_resolves_through_role(
    db_session: AsyncSession,
) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    user_repo = UserRepository(db_session)

    user = await user_repo.create(email="effective@example.com", hashed_password=hash_password("x"))
    role = await role_repo.create(name="EffectiveRole")
    read_perm = await permission_repo.create(resource="users", action="read")
    update_perm = await permission_repo.create(resource="users", action="update")

    await role_repo.assign_permission(role, read_perm)
    await role_repo.assign_permission(role, update_perm)
    await role_repo.assign_role_to_user(user, role)

    effective = await role_repo.get_user_effective_permissions(user)

    assert effective == {"users:read", "users:update"}


async def test_get_user_effective_permissions_empty_for_user_without_roles(
    db_session: AsyncSession,
) -> None:
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.create(email="noroles@example.com", hashed_password=hash_password("x"))

    effective = await role_repo.get_user_effective_permissions(user)

    assert effective == set()


async def test_get_user_effective_permissions_deduplicates_across_roles(
    db_session: AsyncSession,
) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    user_repo = UserRepository(db_session)

    user = await user_repo.create(email="multirole@example.com", hashed_password=hash_password("x"))
    role_a = await role_repo.create(name="RoleA")
    role_b = await role_repo.create(name="RoleB")
    shared_perm = await permission_repo.create(resource="users", action="read")

    await role_repo.assign_permission(role_a, shared_perm)
    await role_repo.assign_permission(role_b, shared_perm)
    await role_repo.assign_role_to_user(user, role_a)
    await role_repo.assign_role_to_user(user, role_b)

    effective = await role_repo.get_user_effective_permissions(user)

    assert effective == {"users:read"}
