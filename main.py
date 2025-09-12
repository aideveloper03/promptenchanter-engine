"""
PromptEnchanter - Enterprise-grade AI Prompt Enhancement Service

This is the main entry point for the PromptEnchanter application.
"""
import uvicorn
from app.core.app import app
from app.config.settings import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )