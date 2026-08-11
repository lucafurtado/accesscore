from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


async def test_create_and_get_by_email(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    created = await repo.create(
        email="alice@example.com", hashed_password="hashed", full_name="Alice"
    )
    fetched = await repo.get_by_email("alice@example.com")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.full_name == "Alice"


async def test_get_by_email_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    result = await repo.get_by_email("nobody@example.com")

    assert result is None


async def test_get_by_id(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    created = await repo.create(email="bob@example.com", hashed_password="hashed")

    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.email == "bob@example.com"


async def test_update_last_login_sets_timestamp(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="carol@example.com", hashed_password="hashed")
    assert user.last_login_at is None

    await repo.update_last_login(user)

    assert user.last_login_at is not None


async def test_update_password_changes_hash(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="dave@example.com", hashed_password="old-hash")

    await repo.update_password(user, "new-hash")

    assert user.hashed_password == "new-hash"
