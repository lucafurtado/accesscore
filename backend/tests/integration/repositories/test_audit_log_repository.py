import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository


async def test_create_persists_entry(db_session: AsyncSession) -> None:
    repo = AuditLogRepository(db_session)

    entry = await repo.create(
        actor_user_id=None,
        action="auth.login_failed",
        resource_type="auth",
        resource_id=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
        context={"attempted_email": "nobody@example.com"},
    )

    assert entry.id is not None
    assert entry.action == "auth.login_failed"
    assert entry.context == {"attempted_email": "nobody@example.com"}


async def test_list_paginated_orders_newest_first(db_session: AsyncSession) -> None:
    # created_at uses server_default=func.now(), which returns transaction
    # start time, not per-statement wall-clock time. All three creates below
    # share this test's single uncommitted transaction, so without an
    # explicit stagger, created_at ties and ordering falls back to a random
    # id tiebreak. Staggering makes the newest-first assertion deterministic
    # without changing production behavior (each real request is its own
    # transaction). created_at can't be fixed up with an UPDATE after the
    # fact - the append-only trigger (correctly) rejects that - so it's set
    # directly at construction time here instead, bypassing the repository.
    repo = AuditLogRepository(db_session)
    for i in range(3):
        entry = AuditLog(
            actor_user_id=None,
            action=f"test.action.{i}",
            resource_type=None,
            resource_id=None,
            ip_address=None,
            user_agent=None,
            context=None,
            created_at=datetime.now(UTC) + timedelta(seconds=i),
        )
        db_session.add(entry)
        await db_session.flush()

    page, next_cursor, has_more = await repo.list_paginated(cursor=None, limit=2)

    assert len(page) == 2
    assert has_more is True
    assert next_cursor is not None
    assert page[0].action == "test.action.2"


async def test_list_paginated_filters_by_action(db_session: AsyncSession) -> None:
    repo = AuditLogRepository(db_session)
    await repo.create(
        actor_user_id=None,
        action="user.created",
        resource_type=None,
        resource_id=None,
        ip_address=None,
        user_agent=None,
        context=None,
    )
    await repo.create(
        actor_user_id=None,
        action="user.disabled",
        resource_type=None,
        resource_id=None,
        ip_address=None,
        user_agent=None,
        context=None,
    )

    page, _, _ = await repo.list_paginated(cursor=None, limit=50, action="user.created")

    assert all(entry.action == "user.created" for entry in page)
    assert len(page) == 1


async def test_list_paginated_filters_by_actor_user_id(db_session: AsyncSession) -> None:
    repo = AuditLogRepository(db_session)
    user_repo = UserRepository(db_session)
    actor = await user_repo.create(email="actor@example.com", hashed_password=hash_password("x"))

    await repo.create(
        actor_user_id=actor.id,
        action="test.actor.action",
        resource_type=None,
        resource_id=None,
        ip_address=None,
        user_agent=None,
        context=None,
    )
    await repo.create(
        actor_user_id=None,
        action="test.other.action",
        resource_type=None,
        resource_id=None,
        ip_address=None,
        user_agent=None,
        context=None,
    )

    page, _, _ = await repo.list_paginated(cursor=None, limit=50, actor_user_id=actor.id)

    assert len(page) == 1
    assert page[0].actor_user_id == actor.id


async def test_list_paginated_filters_by_resource(db_session: AsyncSession) -> None:
    repo = AuditLogRepository(db_session)
    target_id = uuid.uuid4()
    await repo.create(
        actor_user_id=None,
        action="test.resource.match",
        resource_type="role",
        resource_id=target_id,
        ip_address=None,
        user_agent=None,
        context=None,
    )
    await repo.create(
        actor_user_id=None,
        action="test.resource.miss",
        resource_type="role",
        resource_id=uuid.uuid4(),
        ip_address=None,
        user_agent=None,
        context=None,
    )

    page, _, _ = await repo.list_paginated(
        cursor=None, limit=50, resource_type="role", resource_id=target_id
    )

    assert len(page) == 1
    assert page[0].resource_id == target_id


async def test_audit_logs_are_append_only(db_session: AsyncSession) -> None:
    """The audit_logs_no_update_delete DB trigger must reject UPDATE/DELETE.

    This is the real enforcement mechanism (see the add_audit_logs_table
    migration); AuditLogRepository deliberately exposes no update/delete
    methods as a redundant, code-level second layer.
    """
    repo = AuditLogRepository(db_session)
    entry = await repo.create(
        actor_user_id=None,
        action="test.immutable",
        resource_type=None,
        resource_id=None,
        ip_address=None,
        user_agent=None,
        context=None,
    )

    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(
            update(AuditLog).where(AuditLog.id == entry.id).values(action="tampered")
        )
