"""Deterministic, idempotent RBAC seed data for development/demo environments.

Run with: python -m app.db.seed
"""

import asyncio

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

DEFAULT_PERMISSIONS: list[tuple[str, str, str]] = [
    ("users", "read", "View user accounts"),
    ("users", "create", "Create new user accounts"),
    ("users", "update", "Update existing user accounts"),
    ("users", "disable", "Disable user accounts"),
    ("roles", "read", "View roles"),
    ("roles", "manage", "Create, update, and delete roles; manage role permissions"),
    ("permissions", "read", "View permissions"),
    ("permissions", "manage", "Create and delete permissions"),
    ("audit_logs", "read", "View audit logs"),
]

DEFAULT_ROLES: dict[str, list[str]] = {
    "Admin": [
        "users:read",
        "users:create",
        "users:update",
        "users:disable",
        "roles:read",
        "roles:manage",
        "permissions:read",
        "permissions:manage",
        "audit_logs:read",
    ],
    "Manager": ["users:read", "users:update", "roles:read"],
    "Analyst": ["users:read"],
}


async def seed_rbac(permission_repo: PermissionRepository, role_repo: RoleRepository) -> None:
    for resource, action, description in DEFAULT_PERMISSIONS:
        if not await permission_repo.exists(resource, action):
            await permission_repo.create(resource, action, description)

    for role_name, permission_keys in DEFAULT_ROLES.items():
        role = await role_repo.get_by_name(role_name)
        if role is None:
            role = await role_repo.create(role_name)

        for key in permission_keys:
            resource, action = key.split(":")
            permission = await permission_repo.get_by_resource_action(resource, action)
            if permission is not None:
                await role_repo.assign_permission(role, permission)


async def seed_dev_admin_user(
    user_repo: UserRepository,
    role_repo: RoleRepository,
    email: str | None,
    password: str | None,
) -> None:
    if not email or not password:
        return

    user = await user_repo.get_by_email(email)
    if user is None:
        user = await user_repo.create(email=email, hashed_password=hash_password(password))

    admin_role = await role_repo.get_by_name("Admin")
    if admin_role is not None:
        await role_repo.assign_role_to_user(user, admin_role)


async def run_seed() -> None:
    async with AsyncSessionLocal() as session:
        permission_repo = PermissionRepository(session)
        role_repo = RoleRepository(session)
        user_repo = UserRepository(session)

        await seed_rbac(permission_repo, role_repo)
        await seed_dev_admin_user(
            user_repo, role_repo, settings.seed_admin_email, settings.seed_admin_password
        )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run_seed())
