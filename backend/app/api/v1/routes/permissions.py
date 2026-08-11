from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_rbac_service, require_permission
from app.models.permission import Permission
from app.models.user import User
from app.schemas.rbac import PermissionCreate, PermissionResponse
from app.services.rbac_service import RBACService

router = APIRouter()


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    _: User = Depends(require_permission("permissions:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> list[Permission]:
    return await rbac_service.list_permissions()


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreate,
    _: User = Depends(require_permission("permissions:manage")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> Permission:
    return await rbac_service.create_permission(
        payload.resource, payload.action, payload.description
    )
