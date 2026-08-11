"""Dedicated RBAC integration tests, exercised through the real HTTP API.

Some of these properties are already exercised incidentally by the endpoint
tests in test_rbac_management.py and the dependency tests in
test_require_permission.py; this file demonstrates each one explicitly and
by name, as its own scenario.

Two of the spec's illustrative examples reference permissions on endpoints
that don't exist yet (`users:read`/`users:update` gating a user-management
endpoint) since full user CRUD is Milestone 3's job. Those scenarios are
adapted here to use permissions that actually gate real endpoints today
(`roles:read`/`roles:manage`) — the mechanism under test (dynamic,
DB-resolved authorization) is identical regardless of which permission key
is used.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


async def _create_user_with_permissions(
    db_session: AsyncSession, email: str, permission_keys: list[str]
) -> tuple[User, str]:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    user = await user_repo.create(email=email, hashed_password=hash_password("x"))

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


# --- 1. Permission resolution: User -> Role -> Permission ---


async def test_permission_resolution_through_user_role_permission_chain(
    db_session: AsyncSession,
) -> None:
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)
    user_repo = UserRepository(db_session)

    user = await user_repo.create(email="resolution@example.com", hashed_password="hashed")
    role = await role_repo.create(name="ResolutionRole")
    read_perm = await permission_repo.create(resource="users", action="read")
    update_perm = await permission_repo.create(resource="users", action="update")

    await role_repo.assign_permission(role, read_perm)
    await role_repo.assign_permission(role, update_perm)
    await role_repo.assign_role_to_user(user, role)

    effective = await role_repo.get_user_effective_permissions(user)

    assert effective == {"users:read", "users:update"}


# --- 2. Positive authorization ---


async def test_user_with_required_permission_can_access_endpoint(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token = await _create_user_with_permissions(
        db_session, "positive-auth@example.com", ["roles:read"]
    )

    response = await client.get("/api/v1/roles", headers=_auth_headers(token))

    assert response.status_code == 200


# --- 3. Negative authorization ---


async def test_user_without_required_permission_receives_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token = await _create_user_with_permissions(
        db_session, "negative-auth@example.com", ["roles:read"]
    )

    response = await client.post(
        "/api/v1/roles", json={"name": "ShouldBeBlocked"}, headers=_auth_headers(token)
    )

    assert response.status_code == 403


# --- 4. Authentication boundary ---


async def test_unauthenticated_request_receives_401_not_403(client: AsyncClient) -> None:
    response = await client.get("/api/v1/roles")

    assert response.status_code == 401


# --- 5. Dynamic permission changes ---


async def test_removing_permission_denies_next_request_with_same_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, token = await _create_user_with_permissions(
        db_session, "dynamic-perm@example.com", ["roles:manage"]
    )
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    first_attempt = await client.post(
        "/api/v1/roles", json={"name": "BeforeRevoke"}, headers=_auth_headers(token)
    )
    assert first_attempt.status_code == 201

    roles = await role_repo.list_user_roles(user)
    manage_permission = await permission_repo.get_by_resource_action("roles", "manage")
    assert manage_permission is not None
    for role in roles:
        await role_repo.remove_permission(role, manage_permission)

    second_attempt = await client.post(
        "/api/v1/roles", json={"name": "AfterRevoke"}, headers=_auth_headers(token)
    )
    assert second_attempt.status_code == 403


# --- 6. Role assignment changes effective permissions ---


async def test_assigning_and_removing_role_changes_access_for_same_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target_user, target_token = await _create_user_with_permissions(
        db_session, "role-assignment-target@example.com", []
    )
    _, admin_token = await _create_user_with_permissions(
        db_session,
        "role-assignment-admin@example.com",
        ["roles:manage", "roles:read", "permissions:read"],
    )
    admin_headers = _auth_headers(admin_token)

    before_assignment = await client.get("/api/v1/roles", headers=_auth_headers(target_token))
    assert before_assignment.status_code == 403

    role_resp = await client.post(
        "/api/v1/roles", json={"name": "GrantsReadAccess"}, headers=admin_headers
    )
    role_id = role_resp.json()["id"]
    perm_resp = await client.get("/api/v1/permissions", headers=admin_headers)
    roles_read_id = next(
        p["id"] for p in perm_resp.json() if p["resource"] == "roles" and p["action"] == "read"
    )
    await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": roles_read_id},
        headers=admin_headers,
    )

    await client.post(
        f"/api/v1/users/{target_user.id}/roles", json={"role_id": role_id}, headers=admin_headers
    )

    after_assignment = await client.get("/api/v1/roles", headers=_auth_headers(target_token))
    assert after_assignment.status_code == 200

    await client.delete(f"/api/v1/users/{target_user.id}/roles/{role_id}", headers=admin_headers)

    after_removal = await client.get("/api/v1/roles", headers=_auth_headers(target_token))
    assert after_removal.status_code == 403


# --- 7. Privilege escalation prevention ---


async def test_user_cannot_assign_privileged_role_to_self(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    manager, manager_token = await _create_user_with_permissions(
        db_session, "escalation-self@example.com", ["roles:manage"]
    )
    headers = _auth_headers(manager_token)

    role_resp = await client.post("/api/v1/roles", json={"name": "PrivilegedRole"}, headers=headers)
    role_id = role_resp.json()["id"]

    response = await client.post(
        f"/api/v1/users/{manager.id}/roles", json={"role_id": role_id}, headers=headers
    )

    assert response.status_code == 403


async def test_user_cannot_grant_permissions_via_direct_api_call_without_manage_permission(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    low_priv_user, low_priv_token = await _create_user_with_permissions(
        db_session, "escalation-direct@example.com", ["roles:read"]
    )
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    own_roles = await role_repo.list_user_roles(low_priv_user)
    own_role_id = own_roles[0].id
    manage_permission = await permission_repo.get_by_resource_action("roles", "manage")
    assert manage_permission is None

    response = await client.post(
        f"/api/v1/roles/{own_role_id}/permissions",
        json={"permission_id": str(uuid.uuid4())},
        headers=_auth_headers(low_priv_token),
    )

    assert response.status_code == 403


async def test_privilege_escalation_bypass_attempt_via_unauthenticated_call_fails(
    client: AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/users/{uuid.uuid4()}/roles", json={"role_id": str(uuid.uuid4())}
    )

    assert response.status_code == 401
