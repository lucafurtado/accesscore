from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard defensive headers to every response.

    These are cheap, well-understood browser instructions - not a
    substitute for the actual authorization checks every route already
    performs. HSTS is safe to send even from a plain-HTTP origin (e.g.
    local dev): browsers only start enforcing it once they've received it
    over a connection they already trust, which in practice means it's a
    no-op locally and takes effect once the deployed app is served over
    HTTPS (as both Render and Vercel do by default).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
