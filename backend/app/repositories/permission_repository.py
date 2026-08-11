import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, resource: str, action: str, description: str | None = None
    ) -> Permission:
        permission = Permission(resource=resource, action=action, description=description)
        self._session.add(permission)
        await self._session.flush()
        return permission

    async def get_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        return await self._session.get(Permission, permission_id)

    async def get_by_resource_action(self, resource: str, action: str) -> Permission | None:
        result = await self._session.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Permission]:
        result = await self._session.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        )
        return list(result.scalars().all())

    async def exists(self, resource: str, action: str) -> bool:
        return await self.get_by_resource_action(resource, action) is not None

    async def delete(self, permission: Permission) -> None:
        await self._session.delete(permission)
        await self._session.flush()
