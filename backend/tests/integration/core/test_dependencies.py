import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password
from app.repositories.user_repository import UserRepository


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_missing_credentials_raises_401(db_session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, session=db_session)

    assert exc_info.value.status_code == 401


async def test_malformed_token_raises_401(db_session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer("not-a-jwt"), session=db_session)

    assert exc_info.value.status_code == 401


async def test_expired_token_raises_401(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now - timedelta(minutes=30),
            "exp": now - timedelta(minutes=15),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(expired_token), session=db_session)

    assert exc_info.value.status_code == 401


async def test_tampered_token_raises_401(db_session: AsyncSession) -> None:
    token = create_access_token(uuid.uuid4())
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(tampered), session=db_session)

    assert exc_info.value.status_code == 401


async def test_nonexistent_user_raises_401(db_session: AsyncSession) -> None:
    token = create_access_token(uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), session=db_session)

    assert exc_info.value.status_code == 401


async def test_inactive_user_raises_401(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="inactive@example.com", hashed_password=hash_password("x"))
    user.is_active = False
    await db_session.flush()
    token = create_access_token(user.id)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), session=db_session)

    assert exc_info.value.status_code == 401


async def test_valid_token_returns_active_user(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="active@example.com", hashed_password=hash_password("x"))
    token = create_access_token(user.id)

    result = await get_current_user(credentials=_bearer(token), session=db_session)

    assert result.id == user.id
