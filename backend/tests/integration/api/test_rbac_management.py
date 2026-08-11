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


# --- Roles ---


async def test_list_roles_requires_roles_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, no_perm_token = await _create_user_with_permissions(
        db_session, "noperm-roles@example.com", []
    )
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-roles@example.com", ["roles:read"]
    )

    denied = await client.get("/api/v1/roles", headers=_auth_headers(no_perm_token))
    allowed = await client.get("/api/v1/roles", headers=_auth_headers(reader_token))

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)


async def test_create_role_requires_roles_manage_and_rejects_duplicates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-create@example.com", ["roles:read"]
    )
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-create@example.com", ["roles:manage"]
    )

    denied = await client.post(
        "/api/v1/roles", json={"name": "Blocked"}, headers=_auth_headers(reader_token)
    )
    assert denied.status_code == 403

    created = await client.post(
        "/api/v1/roles",
        json={"name": "NewRole", "description": "desc"},
        headers=_auth_headers(manager_token),
    )
    assert created.status_code == 201
    assert created.json()["name"] == "NewRole"

    duplicate = await client.post(
        "/api/v1/roles", json={"name": "NewRole"}, headers=_auth_headers(manager_token)
    )
    assert duplicate.status_code == 409


async def test_get_role_returns_404_for_unknown_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-get@example.com", ["roles:read"]
    )

    response = await client.get(
        f"/api/v1/roles/{uuid.uuid4()}", headers=_auth_headers(reader_token)
    )

    assert response.status_code == 404


async def test_get_update_delete_role_flow(client: AsyncClient, db_session: AsyncSession) -> None:
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-crud@example.com", ["roles:read", "roles:manage"]
    )
    headers = _auth_headers(manager_token)

    created = await client.post("/api/v1/roles", json={"name": "CrudRole"}, headers=headers)
    role_id = created.json()["id"]

    fetched = await client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "CrudRole"

    updated = await client.put(
        f"/api/v1/roles/{role_id}", json={"description": "Updated"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"

    deleted = await client.delete(f"/api/v1/roles/{role_id}", headers=headers)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert gone.status_code == 404


# --- Permissions ---


async def test_list_and_create_permissions_gated_correctly(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-perm@example.com", ["permissions:read"]
    )
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-perm@example.com", ["permissions:manage"]
    )

    denied = await client.post(
        "/api/v1/permissions",
        json={"resource": "widgets", "action": "read"},
        headers=_auth_headers(reader_token),
    )
    assert denied.status_code == 403

    created = await client.post(
        "/api/v1/permissions",
        json={"resource": "widgets", "action": "read"},
        headers=_auth_headers(manager_token),
    )
    assert created.status_code == 201

    duplicate = await client.post(
        "/api/v1/permissions",
        json={"resource": "widgets", "action": "read"},
        headers=_auth_headers(manager_token),
    )
    assert duplicate.status_code == 409

    listed = await client.get("/api/v1/permissions", headers=_auth_headers(reader_token))
    assert listed.status_code == 200
    assert any(p["resource"] == "widgets" and p["action"] == "read" for p in listed.json())


# --- Role <-> Permission assignment ---


async def test_assign_and_remove_permission_from_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-assign@example.com", ["roles:manage", "permissions:manage"]
    )
    headers = _auth_headers(manager_token)

    role_resp = await client.post("/api/v1/roles", json={"name": "AssignTarget"}, headers=headers)
    role_id = role_resp.json()["id"]
    perm_resp = await client.post(
        "/api/v1/permissions", json={"resource": "widgets", "action": "update"}, headers=headers
    )
    permission_id = perm_resp.json()["id"]

    assign = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=headers,
    )
    assert assign.status_code == 204

    assign_unknown = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert assign_unknown.status_code == 404

    remove = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission_id}", headers=headers
    )
    assert remove.status_code == 204


async def test_list_role_permissions_requires_roles_read_and_reflects_assignment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-listperms@example.com", ["roles:manage", "permissions:manage"]
    )
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-listperms@example.com", ["roles:read"]
    )
    _, no_perm_token = await _create_user_with_permissions(
        db_session, "noperm-listperms@example.com", []
    )
    manager_headers = _auth_headers(manager_token)

    role_resp = await client.post(
        "/api/v1/roles", json={"name": "ListPermsRole"}, headers=manager_headers
    )
    role_id = role_resp.json()["id"]
    perm_resp = await client.post(
        "/api/v1/permissions",
        json={"resource": "widgets", "action": "delete"},
        headers=manager_headers,
    )
    permission_id = perm_resp.json()["id"]

    denied = await client.get(
        f"/api/v1/roles/{role_id}/permissions", headers=_auth_headers(no_perm_token)
    )
    assert denied.status_code == 403

    empty = await client.get(
        f"/api/v1/roles/{role_id}/permissions", headers=_auth_headers(reader_token)
    )
    assert empty.status_code == 200
    assert empty.json() == []

    await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=manager_headers,
    )

    populated = await client.get(
        f"/api/v1/roles/{role_id}/permissions", headers=_auth_headers(reader_token)
    )
    assert populated.status_code == 200
    assert [p["id"] for p in populated.json()] == [permission_id]


# --- User <-> Role assignment ---


async def test_list_user_roles_requires_roles_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target_user, _ = await _create_user_with_permissions(db_session, "target-list@example.com", [])
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-userroles@example.com", ["roles:read"]
    )

    response = await client.get(
        f"/api/v1/users/{target_user.id}/roles", headers=_auth_headers(reader_token)
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_assign_and_remove_role_from_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target_user, _ = await _create_user_with_permissions(
        db_session, "target-assign@example.com", []
    )
    _, manager_token = await _create_user_with_permissions(
        db_session, "manager-userroles@example.com", ["roles:manage", "roles:read"]
    )
    headers = _auth_headers(manager_token)

    role_resp = await client.post("/api/v1/roles", json={"name": "AssignableRole"}, headers=headers)
    role_id = role_resp.json()["id"]

    assign = await client.post(
        f"/api/v1/users/{target_user.id}/roles", json={"role_id": role_id}, headers=headers
    )
    assert assign.status_code == 204

    listed = await client.get(f"/api/v1/users/{target_user.id}/roles", headers=headers)
    assert listed.status_code == 200
    assert any(r["id"] == role_id for r in listed.json())

    removed = await client.delete(
        f"/api/v1/users/{target_user.id}/roles/{role_id}", headers=headers
    )
    assert removed.status_code == 204


async def test_assign_role_to_self_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    manager, manager_token = await _create_user_with_permissions(
        db_session, "self-assign@example.com", ["roles:manage"]
    )
    headers = _auth_headers(manager_token)

    role_resp = await client.post("/api/v1/roles", json={"name": "SelfAssignRole"}, headers=headers)
    role_id = role_resp.json()["id"]

    response = await client.post(
        f"/api/v1/users/{manager.id}/roles", json={"role_id": role_id}, headers=headers
    )

    assert response.status_code == 403


async def test_unauthenticated_requests_return_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/roles")

    assert response.status_code == 401
