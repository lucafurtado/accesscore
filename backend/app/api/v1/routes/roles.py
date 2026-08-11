import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    AuditContext,
    get_audit_context,
    get_rbac_service,
    require_permission,
)
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import (
    PermissionAssignmentRequest,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.services.rbac_service import RBACService

router = APIRouter()


async def _get_role_or_404(
    role_id: uuid.UUID,
    rbac_service: RBACService = Depends(get_rbac_service),
) -> Role:
    role = await rbac_service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    _: User = Depends(require_permission("roles:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[Role]:
    return await rbac_service.list_roles()


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    acting_user: User = Depends(require_permission("roles:manage")),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> Role:
    return await rbac_service.create_role(
        payload.name,
        payload.description,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    _: User = Depends(require_permission("roles:read")),
    role: Role = Depends(_get_role_or_404),
) -> Role:
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    payload: RoleUpdate,
    acting_user: User = Depends(require_permission("roles:manage")),
    role: Role = Depends(_get_role_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> Role:
    return await rbac_service.update_role(
        role,
        name=payload.name,
        description=payload.description,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    acting_user: User = Depends(require_permission("roles:manage")),
    role: Role = Depends(_get_role_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    await rbac_service.delete_role(
        role,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def list_role_permissions(
    _: User = Depends(require_permission("roles:read")),
    role: Role = Depends(_get_role_or_404),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[Permission]:
    return await rbac_service.list_role_permissions(role)


@router.post("/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def assign_permission_to_role(
    payload: PermissionAssignmentRequest,
    acting_user: User = Depends(require_permission("roles:manage")),
    role: Role = Depends(_get_role_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    permission = await rbac_service.get_permission_by_id(payload.permission_id)
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    await rbac_service.assign_permission_to_role(
        role,
        permission,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.delete("/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission_from_role(
    permission_id: uuid.UUID,
    acting_user: User = Depends(require_permission("roles:manage")),
    role: Role = Depends(_get_role_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    permission = await rbac_service.get_permission_by_id(permission_id)
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    await rbac_service.remove_permission_from_role(
        role,
        permission,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )
