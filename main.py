"""
PromptEnchanter - Enterprise-grade AI Prompt Enhancement Service

This is the main entry point for the PromptEnchanter application.
"""
import sys
import uvicorn
from app.core.app import app
from app.config.settings import get_settings

settings = get_settings()

# Validate required environment variables
required_vars = ["WAPI_KEY", "WAPI_URL", "SECRET_KEY"]
missing_vars = []

for var in required_vars:
    value = getattr(settings, var.lower(), None)
    if not value:
        missing_vars.append(var)

if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables in your .env file or environment.")
    print("See .env.example for reference.")
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )