from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidRefreshTokenError,
    PrivilegeEscalationError,
)

# Raised by services to reject a request as a normal business outcome (bad
# credentials, a name conflict, a self-escalation attempt) - mapped to a 4xx
# by an @app.exception_handler, not a server error. These must still commit:
# a failed login writes an `auth.login_failed` audit record *before*
# raising AuthenticationError, and a blanket rollback-on-any-exception would
# silently discard that record along with the (correct) rejection - the
# audit trail would then be missing every failed login attempt, which is
# the one signal that matters most for detecting brute-forcing. Every
# current raise site for these four raises before performing any other
# write, so committing here is a no-op in the other cases and a real fix
# only for the audit-on-failure path.
_EXPECTED_DOMAIN_EXCEPTIONS = (
    AuthenticationError,
    InvalidRefreshTokenError,
    AlreadyExistsError,
    PrivilegeEscalationError,
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except _EXPECTED_DOMAIN_EXCEPTIONS:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
        finally:
            await session.close()
