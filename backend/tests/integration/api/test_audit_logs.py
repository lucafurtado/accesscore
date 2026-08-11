from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


async def _create_user_with_permissions(
    db_session: AsyncSession, email: str, permission_keys: list[str], password: str = "x"
) -> tuple[User, str]:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    user = await user_repo.create(email=email, hashed_password=hash_password(password))

    if permission_keys:
        role = await role_repo.create(name=f"role-for-{email}")
        for key in permission_keys:
            resource, action = key.split(":")
            permission = await permission_repo.get_by_resource_action(resource, action)
            if permission is None:
                permission = await permission_repo.create(resource=resource, action=action)
            await role_repo.assign_permission(role, permission)
        await role_repo.assign_role_to_user(user, role)

    token = create_access_token(user.id)
    return user, token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_list_audit_logs_requires_audit_logs_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, no_perm_token = await _create_user_with_permissions(
        db_session, "noperm-audit@example.com", []
    )
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-audit@example.com", ["audit_logs:read"]
    )

    denied = await client.get("/api/v1/audit-logs", headers=_auth_headers(no_perm_token))
    allowed = await client.get("/api/v1/audit-logs", headers=_auth_headers(reader_token))

    assert denied.status_code == 403
    assert allowed.status_code == 200
    body = allowed.json()
    assert "items" in body and "next_cursor" in body and "has_more" in body


async def test_list_audit_logs_records_login_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email="loginaudit@example.com", hashed_password=hash_password("x")
    )
    user.hashed_password = hash_password("correct-password")
    await db_session.flush()

    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-loginaudit@example.com", ["audit_logs:read"]
    )

    await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
    )

    response = await client.get(
        f"/api/v1/audit-logs?action=auth.login_success&actor_user_id={user.id}",
        headers=_auth_headers(reader_token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["actor_user_id"] == str(user.id)


async def test_list_audit_logs_filters_by_resource(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, admin_token = await _create_user_with_permissions(
        db_session, "audit-resource-admin@example.com", ["roles:manage", "audit_logs:read"]
    )
    headers = _auth_headers(admin_token)

    created = await client.post("/api/v1/roles", json={"name": "AuditedRole"}, headers=headers)
    role_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/audit-logs?resource_type=role&resource_id={role_id}", headers=headers
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["action"] == "role.created" for item in items)
    assert all(item["resource_id"] == role_id for item in items)


async def test_unauthenticated_requests_return_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/audit-logs")

    assert response.status_code == 401


async def test_audit_coverage_for_security_sensitive_actions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Every security-sensitive action listed for M3 must produce exactly the
    expected audit event, and none of them may ever leak a secret value."""
    admin_plaintext_password = "coverage-initial-pw-1"
    admin, admin_token = await _create_user_with_permissions(
        db_session,
        "coverage-admin@example.com",
        [
            "users:read",
            "users:create",
            "users:update",
            "users:disable",
            "roles:read",
            "roles:manage",
            "permissions:read",
            "permissions:manage",
        ],
        password=admin_plaintext_password,
    )
    headers = _auth_headers(admin_token)

    # auth.login_failed
    await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "wrong-password"}
    )

    # auth.login_success + capture a fresh, unrevoked token pair for the
    # remaining flow (the fixture-issued token has no refresh token behind it).
    login = await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": admin_plaintext_password}
    )
    tokens = login.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    fresh_headers = {"Authorization": f"Bearer {access_token}"}

    # auth.token_refreshed
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    new_refresh_token = refreshed.json()["refresh_token"]

    # auth.password_changed
    await client.put(
        "/api/v1/auth/change-password",
        json={"current_password": admin_plaintext_password, "new_password": "new-password-123"},
        headers=fresh_headers,
    )
    # change-password revokes all sessions; re-login for the rest of the flow.
    login2 = await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "new-password-123"}
    )
    tokens2 = login2.json()
    fresh_headers = {"Authorization": f"Bearer {tokens2['access_token']}"}

    # auth.logout
    await client.post("/api/v1/auth/logout", json={"refresh_token": tokens2["refresh_token"]})

    # user.created, user.updated, user.disabled, user.reactivated
    created = await client.post(
        "/api/v1/users",
        json={"email": "coverage-target@example.com", "password": "target-pass-123"},
        headers=headers,
    )
    target_id = created.json()["id"]
    await client.put(f"/api/v1/users/{target_id}", json={"full_name": "Renamed"}, headers=headers)
    await client.post(f"/api/v1/users/{target_id}/disable", headers=headers)
    await client.post(f"/api/v1/users/{target_id}/reactivate", headers=headers)

    # role.created, role.updated, permission.created,
    # permission.assigned_to_role, permission.removed_from_role, role.deleted
    role_resp = await client.post("/api/v1/roles", json={"name": "CoverageRole"}, headers=headers)
    role_id = role_resp.json()["id"]
    await client.put(f"/api/v1/roles/{role_id}", json={"description": "updated"}, headers=headers)
    perm_resp = await client.post(
        "/api/v1/permissions", json={"resource": "coverage", "action": "read"}, headers=headers
    )
    permission_id = perm_resp.json()["id"]
    await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=headers,
    )
    await client.delete(f"/api/v1/roles/{role_id}/permissions/{permission_id}", headers=headers)
    await client.delete(f"/api/v1/roles/{role_id}", headers=headers)

    # role.assigned, role.removed
    role2_resp = await client.post(
        "/api/v1/roles", json={"name": "AssignCoverageRole"}, headers=headers
    )
    role2_id = role2_resp.json()["id"]
    await client.post(
        f"/api/v1/users/{target_id}/roles", json={"role_id": role2_id}, headers=headers
    )
    await client.delete(f"/api/v1/users/{target_id}/roles/{role2_id}", headers=headers)

    # --- Verify every expected action was recorded the right number of times ---
    audit_repo = AuditLogRepository(db_session)
    all_entries, _, _ = await audit_repo.list_paginated(cursor=None, limit=200)
    actions_seen = [entry.action for entry in all_entries]

    # This flow deliberately logs in twice (change-password revokes all
    # sessions, forcing a re-login) and creates two roles (CoverageRole,
    # AssignCoverageRole) - every other action happens exactly once.
    expected_counts = {
        "auth.login_failed": 1,
        "auth.login_success": 2,
        "auth.token_refreshed": 1,
        "auth.password_changed": 1,
        "auth.logout": 1,
        "user.created": 1,
        "user.updated": 1,
        "user.disabled": 1,
        "user.reactivated": 1,
        "role.created": 2,
        "role.updated": 1,
        "permission.created": 1,
        "permission.assigned_to_role": 1,
        "permission.removed_from_role": 1,
        "role.deleted": 1,
        "role.assigned": 1,
        "role.removed": 1,
    }
    for action, expected_count in expected_counts.items():
        actual_count = actions_seen.count(action)
        assert (
            actual_count == expected_count
        ), f"expected {expected_count} of {action!r}, saw {actual_count} in {actions_seen}"

    # --- Verify no secret ever leaks into an audit record ---
    forbidden_values = [
        admin_plaintext_password,
        "new-password-123",
        "target-pass-123",
        refresh_token,
        new_refresh_token,
        admin.hashed_password,
        access_token,
    ]
    for entry in all_entries:
        haystacks = [entry.action, str(entry.context), entry.ip_address, entry.user_agent]
        blob = " ".join(str(h) for h in haystacks if h is not None)
        for forbidden in forbidden_values:
            assert forbidden not in blob, f"audit entry {entry.id} leaked a secret value"
