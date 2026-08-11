from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.exceptions import AuthenticationError, InvalidRefreshTokenError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        audit_service: AuditService,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._audit = audit_service

    async def authenticate_user(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        normalized_email = email.strip().lower()
        user = await self._users.get_by_email(normalized_email)

        if user is None or not verify_password(password, user.hashed_password):
            await self._audit.record(
                actor_user_id=None,
                action="auth.login_failed",
                resource_type="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                context={"attempted_email": normalized_email},
            )
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            await self._audit.record(
                actor_user_id=None,
                action="auth.login_failed",
                resource_type="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                context={"attempted_email": normalized_email},
            )
            raise AuthenticationError("Invalid email or password")

        await self._users.update_last_login(user)
        await self._audit.record(
            actor_user_id=user.id,
            action="auth.login_success",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return user

    async def create_session(
        self,
        user: User,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        access_token = create_access_token(user.id)

        raw_refresh_token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh_session(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        token_hash = hash_refresh_token(refresh_token)
        record = await self._refresh_tokens.get_by_token_hash(token_hash)

        if record is None or record.revoked or record.expires_at < datetime.now(UTC):
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        user = await self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        previous_token_id = record.id
        await self._refresh_tokens.revoke(record)

        token_pair = await self.create_session(user, user_agent=user_agent, ip_address=ip_address)

        await self._audit.record(
            actor_user_id=user.id,
            action="auth.token_refreshed",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"previous_refresh_token_id": str(previous_token_id)},
        )

        return token_pair

    async def logout(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        token_hash = hash_refresh_token(refresh_token)
        record = await self._refresh_tokens.get_by_token_hash(token_hash)

        if record is None or record.revoked:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        await self._refresh_tokens.revoke(record)
        await self._audit.record(
            actor_user_id=record.user_id,
            action="auth.logout",
            resource_type="user",
            resource_id=record.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Invalid current password")

        await self._users.update_password(user, hash_password(new_password))
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._audit.record(
            actor_user_id=user.id,
            action="auth.password_changed",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
