from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.db.seed import DEFAULT_PERMISSIONS, DEFAULT_ROLES, seed_dev_admin_user, seed_rbac
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


async def test_seed_rbac_creates_all_permissions_and_roles(db_session: AsyncSession) -> None:
    permission_repo = PermissionRepository(db_session)
    role_repo = RoleRepository(db_session)

    await seed_rbac(permission_repo, role_repo)

    permissions = await permission_repo.list_all()
    assert len(permissions) == len(DEFAULT_PERMISSIONS)
    for resource, action, _ in DEFAULT_PERMISSIONS:
        assert await permission_repo.exists(resource, action)

    roles = await role_repo.list_all()
    assert {r.name for r in roles} == set(DEFAULT_ROLES.keys())


async def test_seed_rbac_assigns_correct_permission_sets_per_role(
    db_session: AsyncSession,
) -> None:
    permission_repo = PermissionRepository(db_session)
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)

    await seed_rbac(permission_repo, role_repo)

    for role_name, expected_keys in DEFAULT_ROLES.items():
        role = await role_repo.get_by_name(role_name)
        assert role is not None

        probe = await user_repo.create(
            email=f"probe-{role_name.lower()}@example.com", hashed_password="hashed"
        )
        await role_repo.assign_role_to_user(probe, role)

        effective = await role_repo.get_user_effective_permissions(probe)
        assert effective == set(expected_keys)


async def test_seed_rbac_is_idempotent(db_session: AsyncSession) -> None:
    permission_repo = PermissionRepository(db_session)
    role_repo = RoleRepository(db_session)

    await seed_rbac(permission_repo, role_repo)
    await seed_rbac(permission_repo, role_repo)

    permissions = await permission_repo.list_all()
    roles = await role_repo.list_all()
    assert len(permissions) == len(DEFAULT_PERMISSIONS)
    assert len(roles) == len(DEFAULT_ROLES)

    admin_role = await role_repo.get_by_name("Admin")
    assert admin_role is not None
    await db_session.refresh(admin_role, attribute_names=["permissions"])
    assert len(admin_role.permissions) == len(DEFAULT_ROLES["Admin"])


async def test_seed_dev_admin_user_skipped_when_credentials_missing(
    db_session: AsyncSession,
) -> None:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    await seed_dev_admin_user(user_repo, role_repo, None, None)
    await seed_dev_admin_user(user_repo, role_repo, "admin@example.com", None)
    await seed_dev_admin_user(user_repo, role_repo, None, "password123")

    assert await user_repo.get_by_email("admin@example.com") is None


async def test_seed_dev_admin_user_creates_user_with_admin_role(
    db_session: AsyncSession,
) -> None:
    permission_repo = PermissionRepository(db_session)
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)

    await seed_rbac(permission_repo, role_repo)
    await seed_dev_admin_user(user_repo, role_repo, "admin@example.com", "adminpassword123")

    user = await user_repo.get_by_email("admin@example.com")
    assert user is not None
    assert verify_password("adminpassword123", user.hashed_password)

    roles = await role_repo.list_user_roles(user)
    assert any(r.name == "Admin" for r in roles)


async def test_seed_dev_admin_user_is_idempotent(db_session: AsyncSession) -> None:
    permission_repo = PermissionRepository(db_session)
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)

    await seed_rbac(permission_repo, role_repo)
    await seed_dev_admin_user(user_repo, role_repo, "admin@example.com", "adminpassword123")
    await seed_dev_admin_user(user_repo, role_repo, "admin@example.com", "adminpassword123")

    user = await user_repo.get_by_email("admin@example.com")
    assert user is not None
    roles = await role_repo.list_user_roles(user)
    admin_roles = [r for r in roles if r.name == "Admin"]
    assert len(admin_roles) == 1
