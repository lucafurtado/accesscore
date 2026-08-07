from fastapi import APIRouter

api_router = APIRouter()

# Milestone 1: auth routes
# from app.api.v1.routes.auth import router as auth_router
# api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Milestone 2: roles and permissions routes
# from app.api.v1.routes.roles import router as roles_router
# api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
# from app.api.v1.routes.permissions import router as permissions_router
# api_router.include_router(permissions_router, prefix="/permissions", tags=["permissions"])

# Milestone 3: users and audit log routes
# from app.api.v1.routes.users import router as users_router
# api_router.include_router(users_router, prefix="/users", tags=["users"])
# from app.api.v1.routes.audit import router as audit_router
# api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
