import uuid

from app.core.exceptions import AlreadyExistsError, PrivilegeEscalationError
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


class RBACService:
    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_repository: RoleRepository,
        user_repository: UserRepository,
        audit_service: AuditService,
    ) -> None:
        self._permissions = permission_repository
        self._roles = role_repository
        self._users = user_repository
        self._audit = audit_service

    async def has_permission(self, user: User, permission_key: str) -> bool:
        effective = await self._roles.get_user_effective_permissions(user)
        return permission_key in effective

    async def get_effective_permissions(self, user: User) -> set[str]:
        return await self._roles.get_user_effective_permissions(user)

    # --- Lookups (path-parameter resolution for routers) ---

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self._roles.get_by_id(role_id)

    async def get_permission_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        return await self._permissions.get_by_id(permission_id)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    # --- Permission management ---

    async def create_permission(
        self,
        resource: str,
        action: str,
        description: str | None = None,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Permission:
        if await self._permissions.exists(resource, action):
            raise AlreadyExistsError(f"Permission '{resource}:{action}' already exists")
        permission = await self._permissions.create(resource, action, description)
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="permission.created",
            resource_type="permission",
            resource_id=permission.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"resource": resource, "action": action},
        )
        return permission

    async def list_permissions(self) -> list[Permission]:
        return await self._permissions.list_all()

    async def delete_permission(self, permission: Permission) -> None:
        await self._permissions.delete(permission)

    # --- Role management ---

    async def create_role(
        self,
        name: str,
        description: str | None = None,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Role:
        if await self._roles.get_by_name(name) is not None:
            raise AlreadyExistsError(f"Role '{name}' already exists")
        role = await self._roles.create(name, description)
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="role.created",
            resource_type="role",
            resource_id=role.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"name": name},
        )
        return role

    async def update_role(
        self,
        role: Role,
        name: str | None = None,
        description: str | None = None,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Role:
        if name is not None and name != role.name:
            existing = await self._roles.get_by_name(name)
            if existing is not None:
                raise AlreadyExistsError(f"Role '{name}' already exists")

        role_id = role.id
        changed_fields = [
            field
            for field, new_value in (("name", name), ("description", description))
            if new_value is not None
        ]
        updated = await self._roles.update(role, name=name, description=description)

        if changed_fields:
            await self._audit.record(
                actor_user_id=actor_user_id,
                action="role.updated",
                resource_type="role",
                resource_id=role_id,
                ip_address=ip_address,
                user_agent=user_agent,
                context={"changed_fields": changed_fields},
            )
        return updated

    async def delete_role(
        self,
        role: Role,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        role_id, role_name = role.id, role.name
        await self._roles.delete(role)
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="role.deleted",
            resource_type="role",
            resource_id=role_id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"name": role_name},
        )

    async def list_roles(self) -> list[Role]:
        return await self._roles.list_all()

    async def list_role_permissions(self, role: Role) -> list[Permission]:
        return await self._roles.list_permissions(role)

    async def assign_permission_to_role(
        self,
        role: Role,
        permission: Permission,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._roles.assign_permission(role, permission)
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="permission.assigned_to_role",
            resource_type="role",
            resource_id=role.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"permission_id": str(permission.id)},
        )

    async def remove_permission_from_role(
        self,
        role: Role,
        permission: Permission,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._roles.remove_permission(role, permission)
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="permission.removed_from_role",
            resource_type="role",
            resource_id=role.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"permission_id": str(permission.id)},
        )

    # --- User-role management ---

    async def assign_role_to_user(
        self,
        acting_user: User,
        target_user: User,
        role: Role,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if acting_user.id == target_user.id:
            raise PrivilegeEscalationError("Users cannot assign roles to themselves")
        await self._roles.assign_role_to_user(target_user, role)
        await self._audit.record(
            actor_user_id=acting_user.id,
            action="role.assigned",
            resource_type="user",
            resource_id=target_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"role_id": str(role.id), "role_name": role.name},
        )

    async def remove_role_from_user(
        self,
        acting_user: User,
        target_user: User,
        role: Role,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._roles.remove_role_from_user(target_user, role)
        await self._audit.record(
            actor_user_id=acting_user.id,
            action="role.removed",
            resource_type="user",
            resource_id=target_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"role_id": str(role.id), "role_name": role.name},
        )

    async def list_user_roles(self, user: User) -> list[Role]:
        return await self._roles.list_user_roles(user)
