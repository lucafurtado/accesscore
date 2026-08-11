import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import fetch_cursor_page
from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Read/write access to the append-only audit_logs table.

    Deliberately exposes no update/delete methods: the
    audit_logs_no_update_delete DB trigger enforces append-only at the
    schema level, and this repository mirrors that at the code level rather
    than tempting a future caller to try.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        action: str,
        resource_type: str | None,
        resource_id: uuid.UUID | None,
        ip_address: str | None,
        user_agent: str | None,
        context: dict[str, Any] | None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            context=context,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_paginated(
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
        stmt: Select[tuple[AuditLog]] = select(AuditLog)
        if actor_user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if created_after is not None:
            stmt = stmt.where(AuditLog.created_at >= created_after)
        if created_before is not None:
            stmt = stmt.where(AuditLog.created_at <= created_before)

        items, next_cursor, has_more = await fetch_cursor_page(
            self._session,
            stmt,
            order_column=AuditLog.created_at,
            id_column=AuditLog.id,
            cursor=cursor,
            limit=limit,
        )
        return list(items), next_cursor, has_more
