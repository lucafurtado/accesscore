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


# --- List / stats ---


async def test_list_users_requires_users_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, no_perm_token = await _create_user_with_permissions(
        db_session, "noperm-list@example.com", []
    )
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-list@example.com", ["users:read"]
    )

    denied = await client.get("/api/v1/users", headers=_auth_headers(no_perm_token))
    allowed = await client.get("/api/v1/users", headers=_auth_headers(reader_token))

    assert denied.status_code == 403
    assert allowed.status_code == 200
    body = allowed.json()
    assert "items" in body
    assert "next_cursor" in body
    assert "has_more" in body


async def test_list_users_pagination_returns_distinct_pages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_repo = UserRepository(db_session)
    for i in range(3):
        await user_repo.create(email=f"paged-{i}@example.com", hashed_password="hashed")
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-paging@example.com", ["users:read"]
    )
    headers = _auth_headers(reader_token)

    first = await client.get("/api/v1/users?limit=2", headers=headers)
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"] is not None

    second = await client.get(
        f"/api/v1/users?limit=2&cursor={first_body['next_cursor']}", headers=headers
    )
    assert second.status_code == 200
    second_body = second.json()

    first_ids = {item["id"] for item in first_body["items"]}
    second_ids = {item["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


async def test_get_user_stats_requires_users_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-stats@example.com", ["users:read"]
    )

    response = await client.get("/api/v1/users/stats", headers=_auth_headers(reader_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["active"] >= 1


# --- Self-service ---


async def test_get_my_profile_requires_no_special_permission(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, token = await _create_user_with_permissions(db_session, "self-profile@example.com", [])

    response = await client.get("/api/v1/users/me", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert "hashed_password" not in response.text


async def test_get_my_permissions_returns_effective_set(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token = await _create_user_with_permissions(
        db_session, "self-permissions@example.com", ["users:read", "roles:read"]
    )

    response = await client.get("/api/v1/users/me/permissions", headers=_auth_headers(token))

    assert response.status_code == 200
    assert set(response.json()) == {"users:read", "roles:read"}


# --- Create ---


async def test_create_user_requires_users_create_and_rejects_duplicates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-create@example.com", ["users:read"]
    )
    _, creator_token = await _create_user_with_permissions(
        db_session, "creator@example.com", ["users:create"]
    )

    denied = await client.post(
        "/api/v1/users",
        json={"email": "blocked@example.com", "password": "password123"},
        headers=_auth_headers(reader_token),
    )
    assert denied.status_code == 403

    created = await client.post(
        "/api/v1/users",
        json={"email": "carlos@example.com", "password": "password123", "full_name": "Carlos"},
        headers=_auth_headers(creator_token),
    )
    assert created.status_code == 201
    assert created.json()["email"] == "carlos@example.com"
    assert "hashed_password" not in created.text
    assert "password" not in created.json()

    duplicate = await client.post(
        "/api/v1/users",
        json={"email": "carlos@example.com", "password": "password123"},
        headers=_auth_headers(creator_token),
    )
    assert duplicate.status_code == 409


# --- Get / update ---


async def test_get_user_returns_404_for_unknown_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-get@example.com", ["users:read"]
    )

    response = await client.get(
        f"/api/v1/users/{uuid.uuid4()}", headers=_auth_headers(reader_token)
    )

    assert response.status_code == 404


async def test_update_user_requires_users_update(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target, _ = await _create_user_with_permissions(db_session, "update-target@example.com", [])
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-update@example.com", ["users:read"]
    )
    _, updater_token = await _create_user_with_permissions(
        db_session, "updater@example.com", ["users:update"]
    )

    denied = await client.put(
        f"/api/v1/users/{target.id}",
        json={"full_name": "Blocked"},
        headers=_auth_headers(reader_token),
    )
    assert denied.status_code == 403

    updated = await client.put(
        f"/api/v1/users/{target.id}",
        json={"full_name": "Updated Name"},
        headers=_auth_headers(updater_token),
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Name"


async def test_update_user_rejects_duplicate_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user_with_permissions(db_session, "taken-email@example.com", [])
    target, _ = await _create_user_with_permissions(db_session, "wants-email@example.com", [])
    _, updater_token = await _create_user_with_permissions(
        db_session, "updater-dup@example.com", ["users:update"]
    )

    response = await client.put(
        f"/api/v1/users/{target.id}",
        json={"email": "taken-email@example.com"},
        headers=_auth_headers(updater_token),
    )

    assert response.status_code == 409


# --- Disable / reactivate ---


async def test_disable_and_reactivate_user_flow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target, _ = await _create_user_with_permissions(db_session, "disable-target@example.com", [])
    _, admin_token = await _create_user_with_permissions(
        db_session, "disabler@example.com", ["users:disable", "users:read"]
    )
    headers = _auth_headers(admin_token)

    disabled = await client.post(f"/api/v1/users/{target.id}/disable", headers=headers)
    assert disabled.status_code == 204

    fetched = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert fetched.json()["is_active"] is False

    reactivated = await client.post(f"/api/v1/users/{target.id}/reactivate", headers=headers)
    assert reactivated.status_code == 204

    fetched_again = await client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert fetched_again.json()["is_active"] is True


async def test_disable_user_blocks_self_disable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin, admin_token = await _create_user_with_permissions(
        db_session, "self-disable@example.com", ["users:disable"]
    )

    response = await client.post(
        f"/api/v1/users/{admin.id}/disable", headers=_auth_headers(admin_token)
    )

    assert response.status_code == 403


# --- Effective permissions for another user ---


async def test_get_user_permissions_requires_users_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target, _ = await _create_user_with_permissions(
        db_session, "perm-target@example.com", ["audit_logs:read"]
    )
    _, reader_token = await _create_user_with_permissions(
        db_session, "reader-permcheck@example.com", ["users:read"]
    )

    response = await client.get(
        f"/api/v1/users/{target.id}/permissions", headers=_auth_headers(reader_token)
    )

    assert response.status_code == 200
    assert response.json() == ["audit_logs:read"]


async def test_unauthenticated_requests_return_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")

    assert response.status_code == 401
