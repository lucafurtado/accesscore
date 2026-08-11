import uuid
from typing import Any
from unittest.mock import create_autospec

import pytest

from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService


@pytest.fixture
def audit_log_repo() -> Any:
    return create_autospec(AuditLogRepository, instance=True)


@pytest.fixture
def service(audit_log_repo: Any) -> AuditService:
    return AuditService(audit_log_repo)


async def test_record_delegates_to_repository_with_all_fields(
    service: AuditService, audit_log_repo: Any
) -> None:
    actor_id = uuid.uuid4()
    resource_id = uuid.uuid4()

    await service.record(
        actor_user_id=actor_id,
        action="user.created",
        resource_type="user",
        resource_id=resource_id,
        ip_address="127.0.0.1",
        user_agent="pytest",
        context={"email": "new@example.com"},
    )

    audit_log_repo.create.assert_awaited_once_with(
        actor_user_id=actor_id,
        action="user.created",
        resource_type="user",
        resource_id=resource_id,
        ip_address="127.0.0.1",
        user_agent="pytest",
        context={"email": "new@example.com"},
    )


async def test_record_allows_none_actor_for_anonymous_events(
    service: AuditService, audit_log_repo: Any
) -> None:
    await service.record(actor_user_id=None, action="auth.login_failed")

    audit_log_repo.create.assert_awaited_once()
    _, kwargs = audit_log_repo.create.await_args
    assert kwargs["actor_user_id"] is None


async def test_list_events_delegates_to_repository(
    service: AuditService, audit_log_repo: Any
) -> None:
    audit_log_repo.list_paginated.return_value = ([], None, False)

    result = await service.list_events(cursor=None, limit=20, action="user.created")

    assert result == ([], None, False)
    audit_log_repo.list_paginated.assert_awaited_once_with(
        cursor=None,
        limit=20,
        actor_user_id=None,
        action="user.created",
        resource_type=None,
        resource_id=None,
        created_after=None,
        created_before=None,
    )
