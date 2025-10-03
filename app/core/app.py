"""
FastAPI application factory for PromptEnchanter
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.v1.api import api_router
from app.api.middleware.logging import LoggingMiddleware, RequestContextMiddleware
from app.api.middleware.rate_limit import limiter
from app.config.settings import get_settings
from app.utils.logger import setup_logging, get_logger
from app.utils.cache import cache_manager
from app.models.schemas import ErrorResponse

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info("Starting PromptEnchanter...")
    
    # Setup logging
    setup_logging()
    
    # Initialize database
    from app.database.database import init_database
    await init_database()
    logger.info("SQLite database initialized")
    
    # Initialize MongoDB
    try:
        from app.database.mongodb import mongodb_manager
        connected = await mongodb_manager.connect()
        if connected:
            logger.info("MongoDB connected successfully")
        else:
            logger.warning("MongoDB connection failed, falling back to SQLite")
    except Exception as e:
        logger.warning(f"MongoDB initialization failed: {e}, falling back to SQLite")
    
    # Create default admin user if none exists
    try:
        from scripts.create_default_admin import create_default_admin
        await create_default_admin()
    except Exception as e:
        logger.warning(f"Could not create default SQLite admin user: {e}")
    
    # Create default MongoDB admin user
    try:
        from scripts.create_default_admin_mongodb import create_default_admin as create_mongodb_admin
        await create_mongodb_admin()
    except Exception as e:
        logger.warning(f"Could not create default MongoDB admin user: {e}")
    
    # Connect to cache
    await cache_manager.connect()
    
    # Start message logging service
    from app.services.message_logging_service import message_logging_service
    await message_logging_service.start()
    logger.info("Message logging service started")
    
    # Start credit reset service
    from app.services.credit_reset_service import credit_reset_service
    if settings.auto_credit_reset_enabled:
        await credit_reset_service.start()
        logger.info("Credit reset service started")
    
    logger.info("PromptEnchanter started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PromptEnchanter...")
    
    # Stop credit reset service
    from app.services.credit_reset_service import credit_reset_service
    await credit_reset_service.stop()
    
    # Stop message logging service
    from app.services.message_logging_service import message_logging_service
    await message_logging_service.stop()
    
    # Disconnect from cache
    await cache_manager.disconnect()
    
    # Close database connections
    from app.database.database import close_database
    await close_database()
    
    # Close MongoDB connections
    try:
        from app.database.mongodb import mongodb_manager
        await mongodb_manager.disconnect()
    except Exception as e:
        logger.warning(f"MongoDB disconnect failed: {e}")
    
    logger.info("PromptEnchanter shut down successfully")


def create_application() -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="PromptEnchanter",
        description="""
        PromptEnchanter is an enterprise-grade service for enhancing user prompts with AI-powered research and prompt engineering techniques.
        
        ## Features
        
        * **Prompt Engineering Styles**: Choose from various prompt engineering methodologies (BPE, BCOT, HCOT, ReAct, ToT)
        * **AI Deep Research**: Automatic research enhancement with internet access and multi-source analysis
        * **Batch Processing**: Process multiple prompts efficiently with parallel or sequential execution
        * **Caching**: Intelligent caching of responses and research results
        * **Rate Limiting**: Enterprise-grade rate limiting and security
        * **Admin Controls**: System management and monitoring capabilities
        
        ## Authentication
        
        All endpoints require Bearer token authentication using your API key.
        
        ## Rate Limits
        
        * Standard endpoints: 100 requests/minute with burst support
        * Batch endpoints: 25 requests/minute with reduced burst
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add middleware
    # Configure CORS origins based on environment
    allowed_origins = ["*"] if settings.debug else [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://your-frontend-domain.com"  # Configure for production
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)
    
    # Add firewall middleware
    from app.security.firewall import firewall_manager, FirewallMiddleware
    app.add_middleware(FirewallMiddleware, firewall_manager=firewall_manager)
    
    # Add comprehensive authentication middleware
    from app.api.middleware.comprehensive_auth import auth_middleware
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(
            "Unhandled exception",
            request_id=request_id,
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal Server Error",
                message="An unexpected error occurred",
                details={"request_id": request_id}
            ).dict()
        )
    
    # Add HTTP exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Handle different detail formats
        if isinstance(exc.detail, dict):
            error_message = exc.detail.get("message", "Request failed")
            details = exc.detail.copy()
            details["request_id"] = request_id
        else:
            error_message = str(exc.detail) if exc.detail else "Request failed"
            details = {"request_id": request_id}
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=error_message,
                message=error_message,
                details=details
            ).dict()
        )
    
    # Include API router
    app.include_router(api_router, prefix="/v1")
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "PromptEnchanter",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
    
    # Health check endpoint (public)
    @app.get("/health", include_in_schema=False)
    async def health():
        return {
            "status": "healthy",
            "service": "PromptEnchanter",
            "version": "1.0.0"
        }
    
    return app


# Create the application instance
app = create_application()