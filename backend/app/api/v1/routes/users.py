import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_rbac_service, require_permission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import RoleAssignmentRequest, RoleResponse
from app.services.rbac_service import RBACService

router = APIRouter()


async def _get_target_user_or_404(
    user_id: uuid.UUID,
    rbac_service: RBACService = Depends(get_rbac_service),
) -> User:
    user = await rbac_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


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
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    role = await rbac_service.get_role_by_id(payload.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await rbac_service.assign_role_to_user(acting_user, target_user, role)


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    role_id: uuid.UUID,
    acting_user: User = Depends(require_permission("roles:manage")),
    target_user: User = Depends(_get_target_user_or_404),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> None:
    role = await rbac_service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await rbac_service.remove_role_from_user(acting_user, target_user, role)
