from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    AuditContext,
    get_audit_context,
    get_auth_service,
    get_current_user,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    audit_ctx: AuditContext = Depends(get_audit_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user = await auth_service.authenticate_user(
        payload.email,
        payload.password,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )

    token_pair = await auth_service.create_session(
        user,
        user_agent=audit_ctx.user_agent,
        ip_address=audit_ctx.ip_address,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    payload: RefreshRequest,
    audit_ctx: AuditContext = Depends(get_audit_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    token_pair = await auth_service.refresh_session(
        payload.refresh_token,
        user_agent=audit_ctx.user_agent,
        ip_address=audit_ctx.ip_address,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    audit_ctx: AuditContext = Depends(get_audit_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    await auth_service.logout(
        payload.refresh_token,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    await auth_service.change_password(
        current_user,
        payload.current_password,
        payload.new_password,
        ip_address=audit_ctx.ip_address,
        user_agent=audit_ctx.user_agent,
    )
