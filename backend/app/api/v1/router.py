from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.permissions import router as permissions_router
from app.api.v1.routes.roles import router as roles_router
from app.api.v1.routes.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(permissions_router, prefix="/permissions", tags=["permissions"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

# users_router currently only exposes the /users/{user_id}/roles sub-resource
# needed by RBAC. Full user management (list/create/update/disable) and audit
# log routes are Milestone 3's job:
# from app.api.v1.routes.audit import router as audit_router
# api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
