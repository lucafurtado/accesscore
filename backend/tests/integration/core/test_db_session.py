"""Exercises app.db.session.get_db()'s own commit/rollback behavior.

Deliberately does *not* use the `client`/`db_session` fixtures from
conftest.py: those override `get_db` entirely (the test's `client` fixture
injects `db_session` directly, bypassing get_db's try/except), so a bug in
get_db's real commit/rollback logic - such as a failed-login audit record
being silently discarded on rollback - is invisible to every test that goes
through `client`. These tests drive the real get_db() generator and verify
what actually lands in the database, via a second, independent session.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import AuthenticationError
from app.db.session import engine as app_engine
from app.db.session import get_db
from app.models.audit_log import AuditLog


@pytest_asyncio.fixture(autouse=True)
async def _dispose_app_engine_after_test() -> AsyncGenerator[None, None]:
    # get_db() uses app.db.session's module-global engine/pool, not the
    # NullPool `db_engine` test fixture. pytest-asyncio hands each test
    # function its own event loop, and a pooled asyncpg connection is bound
    # to the loop that opened it - reusing one across tests raises
    # InterfaceError (same hazard the db_engine fixture's own NullPool
    # comment documents). Disposing after every test forces the next one to
    # open a fresh connection under its own loop instead of recycling a
    # stale one.
    yield
    await app_engine.dispose()


async def _committed(db_engine: AsyncEngine, action: str) -> bool:
    verify_session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with verify_session_factory() as verify_session:
        result = await verify_session.execute(select(AuditLog).where(AuditLog.action == action))
        return result.scalar_one_or_none() is not None


async def test_get_db_commits_a_write_made_before_an_expected_domain_exception(
    db_engine: AsyncEngine,
) -> None:
    # Mirrors AuthService.authenticate_user: write an audit record for the
    # failed attempt, then raise AuthenticationError. A failed login is a
    # normal business outcome (mapped to 401 by an exception handler), not a
    # server error - the audit record documenting the attempt must survive.
    action = "test.login_failed_survives_rollback"
    gen = get_db()
    session = await gen.__anext__()
    session.add(AuditLog(actor_user_id=None, action=action, resource_type="auth"))
    await session.flush()

    with pytest.raises(AuthenticationError):
        await gen.athrow(AuthenticationError("Invalid email or password"))

    assert await _committed(db_engine, action) is True


async def test_get_db_rolls_back_a_write_made_before_an_unexpected_exception(
    db_engine: AsyncEngine,
) -> None:
    # An exception that isn't one of the recognized domain exceptions is a
    # genuine server error - anything written so far in the request is not
    # known-safe to keep, so it must roll back.
    action = "test.unexpected_error_rolls_back"
    gen = get_db()
    session = await gen.__anext__()
    session.add(AuditLog(actor_user_id=None, action=action, resource_type="auth"))
    await session.flush()

    with pytest.raises(ValueError):
        await gen.athrow(ValueError("something unrelated broke"))

    assert await _committed(db_engine, action) is False


async def test_get_db_commits_on_the_normal_success_path(db_engine: AsyncEngine) -> None:
    action = "test.success_path_commits"
    gen = get_db()
    session = await gen.__anext__()
    session.add(AuditLog(actor_user_id=None, action=action, resource_type="auth"))
    await session.flush()

    # No exception raised: driving the generator to exhaustion mirrors a
    # route handler returning normally.
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    assert await _committed(db_engine, action) is True
