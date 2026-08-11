class AuthenticationError(Exception):
    """Raised for invalid login credentials or a failed password check.

    Deliberately generic: callers must not use this to distinguish "wrong
    password" from "unknown email" or "inactive account" in any response,
    since doing so enables account enumeration.
    """


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token is unknown, revoked, expired, or its owning user is inactive."""


class AlreadyExistsError(Exception):
    """Raised when attempting to create a role or permission that already exists."""


class PrivilegeEscalationError(Exception):
    """Raised when an operation would let a user expand their own privileges.

    E.g. assigning a role to yourself. This is enforced even when the acting
    user already holds the permission that gates the operation generally.
    """
