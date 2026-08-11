import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


async def _create_user(session: AsyncSession) -> uuid.UUID:
    user_repo = UserRepository(session)
    user = await user_repo.create(email=f"{uuid.uuid4()}@example.com", hashed_password="hashed")
    return user.id


async def test_create_and_get_by_token_hash(db_session: AsyncSession) -> None:
    user_id = await _create_user(db_session)
    repo = RefreshTokenRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    created = await repo.create(user_id=user_id, token_hash="hash123", expires_at=expires_at)
    fetched = await repo.get_by_token_hash("hash123")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.revoked is False


async def test_get_by_token_hash_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = RefreshTokenRepository(db_session)

    result = await repo.get_by_token_hash("does-not-exist")

    assert result is None


async def test_revoke_marks_token_revoked(db_session: AsyncSession) -> None:
    user_id = await _create_user(db_session)
    repo = RefreshTokenRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(days=7)
    token = await repo.create(user_id=user_id, token_hash="hash456", expires_at=expires_at)

    await repo.revoke(token)

    assert token.revoked is True


async def test_revoke_all_for_user_revokes_only_that_users_active_tokens(
    db_session: AsyncSession,
) -> None:
    user_id = await _create_user(db_session)
    other_user_id = await _create_user(db_session)
    repo = RefreshTokenRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    await repo.create(user_id=user_id, token_hash="a", expires_at=expires_at)
    await repo.create(user_id=user_id, token_hash="b", expires_at=expires_at)
    await repo.create(user_id=other_user_id, token_hash="c", expires_at=expires_at)

    await repo.revoke_all_for_user(user_id)

    refreshed_a = await repo.get_by_token_hash("a")
    refreshed_b = await repo.get_by_token_hash("b")
    refreshed_other = await repo.get_by_token_hash("c")

    assert refreshed_a is not None and refreshed_a.revoked is True
    assert refreshed_b is not None and refreshed_b.revoked is True
    assert refreshed_other is not None and refreshed_other.revoked is False
