"""
API v1 router for PromptEnchanter
"""
from fastapi import APIRouter
from app.api.v1.endpoints import chat, batch, admin, user_management, admin_management, support_staff, monitoring

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    chat.router,
    prefix="/prompt",
    tags=["chat"]
)

api_router.include_router(
    batch.router,
    prefix="/batch",
    tags=["batch"]
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"]
)

# User Management Endpoints
api_router.include_router(
    user_management.router,
    prefix="/users",
    tags=["user-management"]
)

# Admin Management Endpoints
api_router.include_router(
    admin_management.router,
    prefix="/admin-panel",
    tags=["admin-panel"]
)

# Support Staff Endpoints
api_router.include_router(
    support_staff.router,
    prefix="/support",
    tags=["support-staff"]
)

# Monitoring & Utility Endpoints
api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["monitoring"]
)