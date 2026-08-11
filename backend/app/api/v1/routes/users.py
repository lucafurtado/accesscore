import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    AuditContext,
    get_audit_context,
    get_current_user,
    get_rbac_service,
    get_user_service,
    require_permission,
)
from app.core.pagination import CursorPage, PaginationParams
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import RoleAssignmentRequest, RoleResponse
from app.schemas.user import UserCreate, UserResponse, UserStatsResponse, UserUpdate
from app.services.rbac_service import RBACService
from app.services.user_service import UserService

router = APIRouter()


async def _get_target_user_or_404(
    user_id: uuid.UUID,
    rbac_service: RBACService = Depends(get_rbac_service),
) -> User:
    user = await rbac_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --- Literal-path routes must be declared before /{user_id} below, since
# Starlette matches by path shape and would otherwise try to parse "me" or
# "stats" as a UUID path parameter and 422 before ever reaching them. ---


@router.get("", response_model=CursorPage[UserResponse])
async def list_users(
    _: User = Depends(require_permission("users:read")),
    pagination: PaginationParams = Depends(),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    user_service: UserService = Depends(get_user_service),
) -> CursorPage[UserResponse]:
    items, next_cursor, has_more = await user_service.list_users(
        cursor=pagination.cursor, limit=pagination.limit, is_active=is_active, q=q
    )
    return CursorPage[UserResponse](
        items=[UserResponse.model_validate(user) for user in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    _: User = Depends(require_permission("users:read")),
    user_service: UserService = Depends(get_user_service),
) -> UserStatsResponse:
    stats = await user_service.get_stats()
    return UserStatsResponse(total=stats.total, active=stats.active)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/permissions", response_model=list[str])
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[str]:
    permissions = await rbac_service.get_effective_permissions(current_user)
    return sorted(permissions)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    acting_user: User = Depends(require_permission("users:create")),
    audit_ctx: AuditContext = Depends(get_audit_context),
    user_service: UserService = Depends(get_user_service),
) -> User:
    return await user_service.create_user(
        payload.email,
        payload.password,
        payload.full_name,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    _: User = Depends(require_permission("users:read")),
    target_user: User = Depends(_get_target_user_or_404),
) -> User:
    return target_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    payload: UserUpdate,
    acting_user: User = Depends(require_permission("users:update")),
    target_user: User = Depends(_get_target_user_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    user_service: UserService = Depends(get_user_service),
) -> User:
    return await user_service.update_user(
        target_user,
        full_name=payload.full_name,
        email=payload.email,
        actor_user_id=acting_user.id,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.post("/{user_id}/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_user(
    acting_user: User = Depends(require_permission("users:disable")),
    target_user: User = Depends(_get_target_user_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    user_service: UserService = Depends(get_user_service),
) -> None:
    await user_service.disable_user(
        acting_user,
        target_user,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.post("/{user_id}/reactivate", status_code=status.HTTP_204_NO_CONTENT)
async def reactivate_user(
    acting_user: User = Depends(require_permission("users:disable")),
    target_user: User = Depends(_get_target_user_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    user_service: UserService = Depends(get_user_service),
) -> None:
    await user_service.reactivate_user(
        acting_user,
        target_user,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.get("/{user_id}/permissions", response_model=list[str])
async def get_user_permissions(
    _: User = Depends(require_permission("users:read")),
    target_user: User = Depends(_get_target_user_or_404),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[str]:
    permissions = await rbac_service.get_effective_permissions(target_user)
    return sorted(permissions)


@router.get("/{user_id}/roles", response_model=list[RoleResponse])
async def list_user_roles(
    _: User = Depends(require_permission("roles:read")),
    target_user: User = Depends(_get_target_user_or_404),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[Role]:
    return await rbac_service.list_user_roles(target_user)


@router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    payload: RoleAssignmentRequest,
    acting_user: User = Depends(require_permission("roles:manage")),
    target_user: User = Depends(_get_target_user_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    role = await rbac_service.get_role_by_id(payload.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await rbac_service.assign_role_to_user(
        acting_user,
        target_user,
        role,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    role_id: uuid.UUID,
    acting_user: User = Depends(require_permission("roles:manage")),
    target_user: User = Depends(_get_target_user_or_404),
    audit_ctx: AuditContext = Depends(get_audit_context),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    role = await rbac_service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await rbac_service.remove_role_from_user(
        acting_user,
        target_user,
        role,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )
