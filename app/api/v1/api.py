"""
API v1 router for PromptEnchanter
"""
from fastapi import APIRouter
from app.api.v1.endpoints import chat, batch, admin

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