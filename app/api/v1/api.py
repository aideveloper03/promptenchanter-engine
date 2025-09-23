"""
API v1 router for PromptEnchanter
"""
from fastapi import APIRouter
from app.api.v1.endpoints import chat, batch, admin, user_management, support, message_logs

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

api_router.include_router(
    batch.router,
    prefix="/batch",
    tags=["batch"]
)

# User Management Routes
api_router.include_router(
    user_management.router,
    tags=["User Management"]
)

# Message Logs Routes
api_router.include_router(
    message_logs.router,
    tags=["Message Logs"]
)

# Admin Routes  
api_router.include_router(
    admin.router,
    tags=["Admin"]
)

# Support Staff Routes
api_router.include_router(
    support.router,
    tags=["Support"]
)