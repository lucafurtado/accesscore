from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


def _build_test_app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected_route(
        user: User = Depends(require_permission("users:read")),
    ) -> dict[str, str]:
        return {"user_id": str(user.id)}

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


async def _create_user_with_permission(
    db_session: AsyncSession,
    email: str,
    resource: str,
    action: str,
    is_active: bool = True,
) -> User:
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    permission_repo = PermissionRepository(db_session)

    user = await user_repo.create(email=email, hashed_password=hash_password("x"))
    if not is_active:
        user.is_active = False
        await db_session.flush()

    role = await role_repo.create(name=f"role-for-{email}")
    permission = await permission_repo.get_by_resource_action(resource, action)
    if permission is None:
        permission = await permission_repo.create(resource=resource, action=action)
    await role_repo.assign_permission(role, permission)
    await role_repo.assign_role_to_user(user, role)

    return user


async def test_valid_permission_allows_access(db_session: AsyncSession) -> None:
    user = await _create_user_with_permission(db_session, "perm-ok@example.com", "users", "read")
    token = create_access_token(user.id)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)


async def test_missing_permission_returns_403(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email="perm-missing@example.com", hashed_password=hash_password("x")
    )
    token = create_access_token(user.id)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


async def test_unauthenticated_request_returns_401_not_403(db_session: AsyncSession) -> None:
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 401


async def test_inactive_user_returns_401(db_session: AsyncSession) -> None:
    user = await _create_user_with_permission(
        db_session, "perm-inactive@example.com", "users", "read", is_active=False
    )
    token = create_access_token(user.id)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_permission_removed_after_token_issuance_denies_access(
    db_session: AsyncSession,
) -> None:
    user = await _create_user_with_permission(
        db_session, "perm-revoked@example.com", "users", "read"
    )
    token = create_access_token(user.id)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_response = await client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert first_response.status_code == 200

        role_repo = RoleRepository(db_session)
        permission_repo = PermissionRepository(db_session)
        roles = await role_repo.list_user_roles(user)
        permission = await permission_repo.get_by_resource_action("users", "read")
        assert permission is not None
        for role in roles:
            await role_repo.remove_permission(role, permission)

        second_response = await client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )

    assert second_response.status_code == 403
