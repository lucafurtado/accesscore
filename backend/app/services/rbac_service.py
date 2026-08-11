import uuid

from app.core.exceptions import AlreadyExistsError, PrivilegeEscalationError
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class RBACService:
    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_repository: RoleRepository,
        user_repository: UserRepository,
    ) -> None:
        self._permissions = permission_repository
        self._roles = role_repository
        self._users = user_repository

    async def has_permission(self, user: User, permission_key: str) -> bool:
        effective = await self._roles.get_user_effective_permissions(user)
        return permission_key in effective

    # --- Lookups (path-parameter resolution for routers) ---

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self._roles.get_by_id(role_id)

    async def get_permission_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        return await self._permissions.get_by_id(permission_id)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    # --- Permission management ---

    async def create_permission(
        self, resource: str, action: str, description: str | None = None
    ) -> Permission:
        if await self._permissions.exists(resource, action):
            raise AlreadyExistsError(f"Permission '{resource}:{action}' already exists")
        return await self._permissions.create(resource, action, description)

    async def list_permissions(self) -> list[Permission]:
        return await self._permissions.list_all()

    async def delete_permission(self, permission: Permission) -> None:
        await self._permissions.delete(permission)

    # --- Role management ---

    async def create_role(self, name: str, description: str | None = None) -> Role:
        if await self._roles.get_by_name(name) is not None:
            raise AlreadyExistsError(f"Role '{name}' already exists")
        return await self._roles.create(name, description)

    async def update_role(
        self, role: Role, name: str | None = None, description: str | None = None
    ) -> Role:
        if name is not None and name != role.name:
            existing = await self._roles.get_by_name(name)
            if existing is not None:
                raise AlreadyExistsError(f"Role '{name}' already exists")
        return await self._roles.update(role, name=name, description=description)

    async def delete_role(self, role: Role) -> None:
        await self._roles.delete(role)

    async def list_roles(self) -> list[Role]:
        return await self._roles.list_all()

    async def assign_permission_to_role(self, role: Role, permission: Permission) -> None:
        await self._roles.assign_permission(role, permission)

    async def remove_permission_from_role(self, role: Role, permission: Permission) -> None:
        await self._roles.remove_permission(role, permission)

    # --- User-role management ---

    async def assign_role_to_user(self, acting_user: User, target_user: User, role: Role) -> None:
        if acting_user.id == target_user.id:
            raise PrivilegeEscalationError("Users cannot assign roles to themselves")
        await self._roles.assign_role_to_user(target_user, role)

    async def remove_role_from_user(self, acting_user: User, target_user: User, role: Role) -> None:
        await self._roles.remove_role_from_user(target_user, role)

    async def list_user_roles(self, user: User) -> list[Role]:
        return await self._roles.list_user_roles(user)
