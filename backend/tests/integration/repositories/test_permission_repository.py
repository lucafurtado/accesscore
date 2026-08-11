import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.permission_repository import PermissionRepository


async def test_create_and_get_by_id(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)

    created = await repo.create(resource="users", action="read", description="Read users")
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.resource == "users"
    assert fetched.action == "read"
    assert fetched.description == "Read users"


async def test_get_by_id_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


async def test_get_by_resource_action(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)
    created = await repo.create(resource="roles", action="manage")

    fetched = await repo.get_by_resource_action("roles", "manage")

    assert fetched is not None
    assert fetched.id == created.id


async def test_get_by_resource_action_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)

    result = await repo.get_by_resource_action("nonexistent", "action")

    assert result is None


async def test_list_all_returns_permissions_ordered_by_resource_and_action(
    db_session: AsyncSession,
) -> None:
    repo = PermissionRepository(db_session)
    await repo.create(resource="users", action="update")
    await repo.create(resource="users", action="create")
    await repo.create(resource="audit_logs", action="read")

    permissions = await repo.list_all()

    keys = [(p.resource, p.action) for p in permissions]
    assert keys == sorted(keys)
    assert ("users", "update") in keys
    assert ("users", "create") in keys
    assert ("audit_logs", "read") in keys


async def test_exists_returns_true_when_present(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)
    await repo.create(resource="permissions", action="read")

    assert await repo.exists("permissions", "read") is True


async def test_exists_returns_false_when_absent(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)

    assert await repo.exists("permissions", "read") is False


async def test_delete_removes_permission(db_session: AsyncSession) -> None:
    repo = PermissionRepository(db_session)
    created = await repo.create(resource="users", action="disable")

    await repo.delete(created)

    assert await repo.get_by_id(created.id) is None
