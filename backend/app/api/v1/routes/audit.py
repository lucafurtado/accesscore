import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_audit_service, require_permission
from app.core.pagination import CursorPage, PaginationParams
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=CursorPage[AuditLogResponse])
async def list_audit_logs(
    _: User = Depends(require_permission("audit_logs:read")),
    pagination: PaginationParams = Depends(),
    actor_user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=50),
    resource_id: uuid.UUID | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    audit_service: AuditService = Depends(get_audit_service),
) -> CursorPage[AuditLogResponse]:
    items, next_cursor, has_more = await audit_service.list_events(
        cursor=pagination.cursor,
        limit=pagination.limit,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        created_after=created_after,
        created_before=created_before,
    )
    return CursorPage[AuditLogResponse](
        items=[AuditLogResponse.model_validate(entry) for entry in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )
