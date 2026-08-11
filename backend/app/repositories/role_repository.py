import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.associations import role_permissions, user_roles
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self._session.add(role)
        await self._session.flush()
        return role

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self._session.get(Role, role_id)

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        result = await self._session.execute(select(Role).order_by(Role.name))
        return list(result.scalars().all())

    async def update(
        self, role: Role, name: str | None = None, description: str | None = None
    ) -> Role:
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        await self._session.flush()
        # Postgres computes updated_at server-side (onupdate=func.now()); refresh
        # so the in-memory object reflects it instead of triggering a lazy
        # attribute load outside the async context during response serialization.
        await self._session.refresh(role)
        return role

    async def delete(self, role: Role) -> None:
        await self._session.delete(role)
        await self._session.flush()

    async def assign_permission(self, role: Role, permission: Permission) -> None:
        await self._session.refresh(role, attribute_names=["permissions"])
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self._session.flush()

    async def remove_permission(self, role: Role, permission: Permission) -> None:
        await self._session.refresh(role, attribute_names=["permissions"])
        if permission in role.permissions:
            role.permissions.remove(permission)
            await self._session.flush()

    async def assign_role_to_user(self, user: User, role: Role) -> None:
        await self._session.refresh(user, attribute_names=["roles"])
        if role not in user.roles:
            user.roles.append(role)
            await self._session.flush()

    async def remove_role_from_user(self, user: User, role: Role) -> None:
        await self._session.refresh(user, attribute_names=["roles"])
        if role in user.roles:
            user.roles.remove(role)
            await self._session.flush()

    async def list_user_roles(self, user: User) -> list[Role]:
        await self._session.refresh(user, attribute_names=["roles"])
        return list(user.roles)

    async def get_user_effective_permissions(self, user: User) -> set[str]:
        stmt = (
            select(Permission.resource, Permission.action)
            .select_from(Permission)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .where(user_roles.c.user_id == user.id)
            .distinct()
        )
        result = await self._session.execute(stmt)
        return {f"{resource}:{action}" for resource, action in result.all()}
