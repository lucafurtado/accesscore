class AuthenticationError(Exception):
    """Raised for invalid login credentials or a failed password check.

    Deliberately generic: callers must not use this to distinguish "wrong
    password" from "unknown email" or "inactive account" in any response,
    since doing so enables account enumeration.
    """


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token is unknown, revoked, expired, or its owning user is inactive."""
