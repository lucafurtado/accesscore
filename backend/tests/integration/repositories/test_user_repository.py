from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


async def _create_with_staggered_timestamp(
    repo: UserRepository, session: AsyncSession, email: str, offset_seconds: int
) -> User:
    # Base.created_at uses server_default=func.now(), which returns the
    # transaction's start time, not per-statement wall-clock time. Every
    # create() in a single test shares one uncommitted transaction (the
    # db_session fixture), so without this, created_at ties across all rows
    # and ordering falls back to a random id tiebreak instead of insertion
    # order. Explicitly staggering created_at makes newest-first assertions
    # deterministic without changing anything about production behavior,
    # where each request is its own transaction.
    user = await repo.create(email=email, hashed_password="hashed")
    user.created_at = datetime.now(UTC) + timedelta(seconds=offset_seconds)
    await session.flush()
    return user


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


async def test_update_profile_updates_only_provided_fields(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(
        email="erin@example.com", hashed_password="hashed", full_name="Original Name"
    )

    updated = await repo.update_profile(user, full_name="New Name")

    assert updated.full_name == "New Name"
    assert updated.email == "erin@example.com"


async def test_set_active_toggles_flag(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="frank@example.com", hashed_password="hashed")
    assert user.is_active is True

    await repo.set_active(user, False)
    assert user.is_active is False

    await repo.set_active(user, True)
    assert user.is_active is True


async def test_count_with_and_without_active_filter(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    active_user = await repo.create(email="active@example.com", hashed_password="hashed")
    inactive_user = await repo.create(email="inactive@example.com", hashed_password="hashed")
    await repo.set_active(inactive_user, False)

    assert await repo.count() >= 2
    active_count = await repo.count(is_active=True)
    inactive_count = await repo.count(is_active=False)

    assert active_user.is_active is True
    assert active_count >= 1
    assert inactive_count >= 1


async def test_list_paginated_orders_newest_first_and_respects_limit(
    db_session: AsyncSession,
) -> None:
    repo = UserRepository(db_session)
    for i in range(3):
        await _create_with_staggered_timestamp(
            repo, db_session, f"page-user-{i}@example.com", offset_seconds=i
        )

    page, next_cursor, has_more = await repo.list_paginated(cursor=None, limit=2)

    assert len(page) == 2
    assert has_more is True
    assert next_cursor is not None
    # Newest first: the last-created user in this batch should lead.
    assert page[0].email == "page-user-2@example.com"


async def test_list_paginated_cursor_continues_without_overlap(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    created = [
        await repo.create(email=f"cursor-user-{i}@example.com", hashed_password="hashed")
        for i in range(3)
    ]

    first_page, cursor, has_more = await repo.list_paginated(cursor=None, limit=2)
    assert has_more is True

    second_page, _, has_more_2 = await repo.list_paginated(cursor=cursor, limit=2)

    first_ids = {u.id for u in first_page}
    second_ids = {u.id for u in second_page}
    assert first_ids.isdisjoint(second_ids)
    assert {u.id for u in created} <= (first_ids | second_ids)
    assert has_more_2 is False


async def test_list_paginated_filters_by_is_active(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    keep = await repo.create(email="filter-active@example.com", hashed_password="hashed")
    disabled = await repo.create(email="filter-inactive@example.com", hashed_password="hashed")
    await repo.set_active(disabled, False)

    page, _, _ = await repo.list_paginated(cursor=None, limit=50, is_active=True)

    ids = {u.id for u in page}
    assert keep.id in ids
    assert disabled.id not in ids


async def test_list_paginated_filters_by_email_search(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    match = await repo.create(email="findme-search@example.com", hashed_password="hashed")
    await repo.create(email="unrelated@example.com", hashed_password="hashed")

    page, _, _ = await repo.list_paginated(cursor=None, limit=50, q="findme")

    ids = {u.id for u in page}
    assert match.id in ids
    assert len(page) == 1
