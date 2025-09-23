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
    
    # Connect to cache
    await cache_manager.connect()
    
    logger.info("PromptEnchanter started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PromptEnchanter...")
    
    # Disconnect from cache
    await cache_manager.disconnect()
    
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)
    
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
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                message="Request failed",
                details={"request_id": request_id}
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