import uuid
from datetime import datetime

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository

# Primitives (plus lists of strings, e.g. changed field names) only, not
# dict[str, Any]: a deliberate guardrail against a call site dumping a full
# payload/model into context and accidentally leaking a sensitive field
# (password, token hash, etc). Every field that goes into context must be
# explicitly picked by the caller.
AuditContextPayload = dict[str, str | int | bool | list[str] | None]


class AuditService:
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_logs = audit_log_repository

    async def record(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        context: AuditContextPayload | None = None,
    ) -> None:
        await self._audit_logs.create(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            context=context,
        )

    async def list_events(
        self,
        *,
        cursor: str | None,
        limit: int,
        actor_user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> tuple[list[AuditLog], str | None, bool]:
        return await self._audit_logs.list_paginated(
            cursor=cursor,
            limit=limit,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            created_after=created_after,
            created_before=created_before,
        )
