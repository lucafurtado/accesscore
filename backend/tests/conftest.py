from collections.abc import AsyncGenerator
from urllib.parse import urlparse

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.rate_limit import reset_rate_limiters
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    # This fixture drops every table at teardown. Refuse to run against
    # anything that isn't clearly a disposable test database, so a
    # misconfigured DATABASE_URL can't wipe a dev/prod schema.
    db_name = urlparse(settings.database_url).path.lstrip("/")
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run tests against database {db_name!r}: DATABASE_URL must point "
            "at a dedicated test database (its name must contain 'test'), since this fixture "
            "drops all tables at session teardown."
        )

    # NullPool: pytest-asyncio gives each test function its own event loop,
    # but asyncpg connections are bound to the loop that created them. A
    # pooled connection reused across loops raises InterfaceError. NullPool
    # opens a fresh connection per checkout instead of reusing one.
    engine = create_async_engine(settings.database_url, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Base.metadata.create_all() only creates tables/columns from ORM
        # metadata; it doesn't run Alembic migrations, so DB-level objects
        # defined only as raw SQL there (the audit_logs append-only trigger,
        # see migrations/versions/..._add_audit_logs_table.py) must be
        # created here too, mirroring that migration's upgrade() step.
        await conn.execute(text("""
                CREATE OR REPLACE FUNCTION audit_logs_deny_mutation() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_logs is append-only';
                END;
                $$ LANGUAGE plpgsql;
                """))
        await conn.execute(text("""
                CREATE TRIGGER audit_logs_no_update_delete
                BEFORE UPDATE OR DELETE ON audit_logs
                FOR EACH ROW EXECUTE FUNCTION audit_logs_deny_mutation();
                """))

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # ASGITransport has no real network, so every test's requests share the
    # same fake client host - without resetting, unrelated tests would
    # eventually collide on the same login/refresh rate-limit budget.
    reset_rate_limiters()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
