import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidRefreshTokenError,
    PrivilegeEscalationError,
)
from app.db.session import engine
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.DEBUG if settings.debug else logging.INFO
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("AccessCore API starting")
    yield
    await engine.dispose()
    logger.info("shut down")


_docs_visible = settings.debug or settings.enable_api_docs

app = FastAPI(
    title="AccessCore",
    description="Enterprise Identity & Access Management Platform",
    version="0.1.0",
    docs_url="/docs" if _docs_visible else None,
    redoc_url="/redoc" if _docs_visible else None,
    openapi_url="/openapi.json" if _docs_visible else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})


@app.exception_handler(InvalidRefreshTokenError)
async def invalid_refresh_token_handler(
    request: Request, exc: InvalidRefreshTokenError
) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": "Invalid or expired refresh token"})


@app.exception_handler(AlreadyExistsError)
async def already_exists_error_handler(request: Request, exc: AlreadyExistsError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(PrivilegeEscalationError)
async def privilege_escalation_error_handler(
    request: Request, exc: PrivilegeEscalationError
) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
async def health_check() -> JSONResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health_check_db_unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "service": "accesscore-api", "database": "down"},
        )

    return JSONResponse(content={"status": "ok", "service": "accesscore-api", "database": "up"})
