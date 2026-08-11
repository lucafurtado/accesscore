import uuid
from dataclasses import dataclass

from app.core.exceptions import AlreadyExistsError, PrivilegeEscalationError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


@dataclass
class UserStats:
    total: int
    active: int


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        audit_service: AuditService,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._audit = audit_service

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    async def list_users(
        self,
        *,
        cursor: str | None,
        limit: int,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[User], str | None, bool]:
        return await self._users.list_paginated(
            cursor=cursor, limit=limit, is_active=is_active, q=q
        )

    async def get_stats(self) -> UserStats:
        total = await self._users.count()
        active = await self._users.count(is_active=True)
        return UserStats(total=total, active=active)

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str | None,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        normalized_email = email.strip().lower()
        if await self._users.get_by_email(normalized_email) is not None:
            raise AlreadyExistsError(f"User '{normalized_email}' already exists")

        user = await self._users.create(
            email=normalized_email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await self._audit.record(
            actor_user_id=actor_user_id,
            action="user.created",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            context={"email": normalized_email},
        )
        return user

    async def update_user(
        self,
        user: User,
        full_name: str | None = None,
        email: str | None = None,
        *,
        actor_user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        normalized_email = email.strip().lower() if email is not None else None
        if normalized_email is not None and normalized_email != user.email:
            existing = await self._users.get_by_email(normalized_email)
            if existing is not None:
                raise AlreadyExistsError(f"User '{normalized_email}' already exists")

        changed_fields = [
            field
            for field, new_value in (("full_name", full_name), ("email", normalized_email))
            if new_value is not None
        ]
        updated = await self._users.update_profile(
            user, full_name=full_name, email=normalized_email
        )

        if changed_fields:
            await self._audit.record(
                actor_user_id=actor_user_id,
                action="user.updated",
                resource_type="user",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                context={"changed_fields": changed_fields},
            )
        return updated

    async def disable_user(
        self,
        acting_user: User,
        target_user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if acting_user.id == target_user.id:
            raise PrivilegeEscalationError("Users cannot disable their own account")

        await self._users.set_active(target_user, False)
        await self._refresh_tokens.revoke_all_for_user(target_user.id)
        await self._audit.record(
            actor_user_id=acting_user.id,
            action="user.disabled",
            resource_type="user",
            resource_id=target_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def reactivate_user(
        self,
        acting_user: User,
        target_user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._users.set_active(target_user, True)
        await self._audit.record(
            actor_user_id=acting_user.id,
            action="user.reactivated",
            resource_type="user",
            resource_id=target_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
