import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import fetch_cursor_page
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str | None = None) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

    async def update_password(self, user: User, hashed_password: str) -> None:
        user.hashed_password = hashed_password
        await self._session.flush()

    async def update_profile(
        self, user: User, full_name: str | None = None, email: str | None = None
    ) -> User:
        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email
        await self._session.flush()
        # Postgres computes updated_at server-side (onupdate=func.now()); refresh
        # so the in-memory object reflects it instead of a lazy load outside the
        # async context during response serialization.
        await self._session.refresh(user)
        return user

    async def set_active(self, user: User, is_active: bool) -> None:
        user.is_active = is_active
        await self._session.flush()
        # Same reason as update_profile above: updated_at is server-computed,
        # so it's expired after flush and must be refreshed here rather than
        # lazily reloaded outside the async context during serialization.
        await self._session.refresh(user)

    async def list_paginated(
        self,
        *,
        cursor: str | None,
        limit: int,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[User], str | None, bool]:
        stmt: Select[tuple[User]] = select(User)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if q:
            stmt = stmt.where(User.email.ilike(f"%{q}%"))

        items, next_cursor, has_more = await fetch_cursor_page(
            self._session,
            stmt,
            order_column=User.created_at,
            id_column=User.id,
            cursor=cursor,
            limit=limit,
        )
        return list(items), next_cursor, has_more

    async def count(self, *, is_active: bool | None = None) -> int:
        stmt = select(func.count()).select_from(User)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        result = await self._session.execute(stmt)
        return result.scalar_one()
