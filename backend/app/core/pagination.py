import base64
import binascii
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None
    has_more: bool


class PaginationParams:
    """Shared query-parameter dependency for cursor-paginated list endpoints."""

    def __init__(
        self,
        limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
        cursor: str | None = Query(default=None),
    ) -> None:
        self.limit = limit
        self.cursor = cursor


class _CursorOrderable(Protocol):
    """Instance-level shape of a row returned by fetch_cursor_page.

    Only used for typing items[-1].created_at/.id in the return path below;
    the query-building side uses explicit order_column/id_column params
    instead of deriving columns from a model class, since those carry
    SQLAlchemy's real class-level InstrumentedAttribute typing and this
    Protocol (correctly) does not.
    """

    id: UUID
    created_at: datetime


def encode_cursor(created_at: datetime, id_: UUID) -> str:
    raw = f"{created_at.isoformat()}|{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID] | None:
    """Decode an opaque pagination cursor.

    Returns None on any malformed input rather than raising: cursors aren't
    signed, so a tampered or garbage cursor simply falls back to the first
    page instead of producing a 500 or leaking anything, since every route
    using this is independently gated by require_permission regardless.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(created_at_str), UUID(id_str)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


async def fetch_cursor_page[ModelT: _CursorOrderable](
    session: AsyncSession,
    stmt: Select[tuple[ModelT]],
    *,
    order_column: InstrumentedAttribute[datetime],
    id_column: InstrumentedAttribute[UUID],
    cursor: str | None,
    limit: int,
) -> tuple[Sequence[ModelT], str | None, bool]:
    """Execute `stmt` as a keyset-paginated query ordered newest-first.

    `order_column`/`id_column` are the model's `created_at`/`id` columns
    (e.g. `AuditLog.created_at`, `AuditLog.id`), passed explicitly rather
    than derived from a model class so they carry SQLAlchemy's real
    class-level column typing. Ordering and the cursor comparison are both
    built from that pair so results stay stable under concurrent inserts
    (unlike OFFSET, which can skip or repeat rows).
    """
    decoded = decode_cursor(cursor) if cursor else None
    if decoded is not None:
        cursor_created_at, cursor_id = decoded
        stmt = stmt.where(tuple_(order_column, id_column) < (cursor_created_at, cursor_id))

    stmt = stmt.order_by(order_column.desc(), id_column.desc()).limit(limit + 1)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None

    return items, next_cursor, has_more
