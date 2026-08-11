"""Milestone 2 acceptance suite: the complete authorization workflow, end-to-end.

Unlike test_rbac_authorization.py (Prompt 10), which mostly mints tokens
directly via create_access_token() to test individual mechanisms in
isolation, this suite drives the *real* /auth/login endpoint throughout --
proving the whole Admin -> Manager -> grant -> revoke workflow the spec
describes actually works through the real API, not just through internals.

As in Prompt 10, the spec's illustrative "users:read" / privileged-action
permissions are adapted to "roles:read" / "roles:manage" since those are the
permissions that actually gate real endpoints in this milestone (full user
CRUD is Milestone 3's job). The mechanism under test -- DB-state-driven,
JWT-independent authorization -- is identical either way.
"""

from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_full_admin_manager_authorization_workflow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    # --- Setup: an Admin account with roles:manage + permissions:manage,
    # capable of running the whole workflow through the management API. ---
    admin_role = await role_repo.create(name="Admin")
    for resource, action in [("roles", "manage"), ("roles", "read"), ("permissions", "manage")]:
        permission = await permission_repo.get_by_resource_action(resource, action)
        if permission is None:
            permission = await permission_repo.create(resource, action)
        await role_repo.assign_permission(admin_role, permission)
    admin_user = await user_repo.create(
        email="admin-acceptance@example.com", hashed_password=hash_password("admin-password-1")
    )
    await role_repo.assign_role_to_user(admin_user, admin_role)

    manager_user = await user_repo.create(
        email="manager-acceptance@example.com",
        hashed_password=hash_password("manager-password-1"),
    )

    # 1. Admin logs in (real login, not a synthetically minted token).
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "admin-password-1"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = _auth_headers(admin_token)

    # 2. Admin creates the Manager role.
    manager_role_resp = await client.post(
        "/api/v1/roles", json={"name": "Manager"}, headers=admin_headers
    )
    assert manager_role_resp.status_code == 201
    manager_role_id = manager_role_resp.json()["id"]

    # 3. Manager role receives the "allowed action" permission (roles:read).
    read_perm_resp = await client.post(
        "/api/v1/permissions", json={"resource": "roles", "action": "read"}, headers=admin_headers
    )
    assert read_perm_resp.status_code in (201, 409)
    if read_perm_resp.status_code == 409:
        existing = await permission_repo.get_by_resource_action("roles", "read")
        assert existing is not None
        read_permission_id = str(existing.id)
    else:
        read_permission_id = read_perm_resp.json()["id"]

    assign_read_resp = await client.post(
        f"/api/v1/roles/{manager_role_id}/permissions",
        json={"permission_id": read_permission_id},
        headers=admin_headers,
    )
    assert assign_read_resp.status_code == 204

    # Admin assigns the Manager role to the manager user.
    assign_role_resp = await client.post(
        f"/api/v1/users/{manager_user.id}/roles",
        json={"role_id": manager_role_id},
        headers=admin_headers,
    )
    assert assign_role_resp.status_code == 204

    # 4. Manager authenticates (real login).
    manager_login = await client.post(
        "/api/v1/auth/login",
        json={"email": manager_user.email, "password": "manager-password-1"},
    )
    assert manager_login.status_code == 200
    manager_token = manager_login.json()["access_token"]
    manager_headers = _auth_headers(manager_token)

    # Verify no roles or permissions are embedded in the JWT: only the
    # minimal identity claims are present.
    payload = jwt.decode(
        manager_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert set(payload.keys()) == {"sub", "iat", "exp", "type"}

    # 5. Manager successfully performs an allowed action.
    allowed_action = await client.get("/api/v1/roles", headers=manager_headers)
    assert allowed_action.status_code == 200

    # 6/7. Manager attempts a privileged action (roles:manage) -> 403.
    privileged_attempt_1 = await client.post(
        "/api/v1/roles", json={"name": "AttemptedByManager"}, headers=manager_headers
    )
    assert privileged_attempt_1.status_code == 403

    # 8. Admin grants the missing permission to the Manager role.
    manage_perm_resp = await client.post(
        "/api/v1/permissions",
        json={"resource": "roles", "action": "manage"},
        headers=admin_headers,
    )
    assert manage_perm_resp.status_code in (201, 409)
    if manage_perm_resp.status_code == 409:
        existing = await permission_repo.get_by_resource_action("roles", "manage")
        assert existing is not None
        manage_permission_id = str(existing.id)
    else:
        manage_permission_id = manage_perm_resp.json()["id"]

    grant_resp = await client.post(
        f"/api/v1/roles/{manager_role_id}/permissions",
        json={"permission_id": manage_permission_id},
        headers=admin_headers,
    )
    assert grant_resp.status_code == 204

    # 9/10. Manager retries with the SAME access token (no new login) ->
    # succeeds. This is only possible because authorization is resolved from
    # current DB state on every request, not cached in the token.
    privileged_attempt_2 = await client.post(
        "/api/v1/roles", json={"name": "CreatedByManager"}, headers=manager_headers
    )
    assert privileged_attempt_2.status_code == 201

    # 11. Admin removes the permission again.
    revoke_resp = await client.delete(
        f"/api/v1/roles/{manager_role_id}/permissions/{manage_permission_id}",
        headers=admin_headers,
    )
    assert revoke_resp.status_code == 204

    # 12/13. Manager retries again, same token -> denied.
    privileged_attempt_3 = await client.post(
        "/api/v1/roles", json={"name": "ShouldFailNow"}, headers=manager_headers
    )
    assert privileged_attempt_3.status_code == 403


async def test_401_means_unauthenticated_403_means_unauthorized(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    # No token at all: 401.
    unauthenticated = await client.get("/api/v1/roles")
    assert unauthenticated.status_code == 401

    # Valid token, authenticated, but missing permission: 403.
    user = await user_repo.create(
        email="boundary-check@example.com", hashed_password=hash_password("boundary-password-1")
    )
    role = await role_repo.create(name="NoPermissionsRole")
    await role_repo.assign_role_to_user(user, role)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "boundary-password-1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    authenticated_but_forbidden = await client.get("/api/v1/roles", headers=_auth_headers(token))
    assert authenticated_but_forbidden.status_code == 403


async def test_authorization_never_trusts_client_supplied_role_or_permission_claims(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A caller cannot influence authorization by sending extra fields the
    schemas don't define (e.g. pretending to already have a role/permission
    in the request body). Only server-resolved DB state is consulted."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email="no-trust-client@example.com", hashed_password=hash_password("no-trust-pw-1")
    )

    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "no-trust-pw-1"}
    )
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/roles",
        json={"name": "SneakyRole", "roles": ["Admin"], "permissions": ["roles:manage"]},
        headers=_auth_headers(token),
    )

    assert response.status_code == 403
