import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService
from app.services.user_service import UserService

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuditContext:
    """IP address and user agent for the current request, for audit records.

    Services never receive the raw Request object (that would break the
    Router -> Service -> Repository layering); routes extract this once via
    Depends(get_audit_context) and pass it down explicitly instead.
    """

    ip_address: str | None
    user_agent: str | None


def get_audit_context(request: Request) -> AuditContext:
    return AuditContext(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def get_audit_service(session: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(AuditLogRepository(session))


def get_auth_service(
    session: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session), audit_service)


def get_rbac_service(
    session: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> RBACService:
    return RBACService(
        PermissionRepository(session),
        RoleRepository(session),
        UserRepository(session),
        audit_service,
    )


def get_user_service(
    session: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> UserService:
    return UserService(UserRepository(session), RefreshTokenRepository(session), audit_service)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise _credentials_exception()

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _credentials_exception() from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise _credentials_exception() from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()

    return user


def require_permission(permission_key: str) -> Callable[..., Coroutine[Any, Any, User]]:
    """Return a dependency that authorizes the current user for `permission_key`.

    Permissions are resolved from current database state on every call, never
    from the JWT, so revoking a permission takes effect on the next request
    even though the caller's access token is still valid.
    """

    async def _dependency(
        current_user: User = Depends(get_current_user),
        rbac_service: RBACService = Depends(get_rbac_service),
    ) -> User:
        if not await rbac_service.has_permission(current_user, permission_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _dependency
