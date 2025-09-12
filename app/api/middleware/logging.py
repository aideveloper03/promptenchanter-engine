"""
Logging middleware for PromptEnchanter
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import get_logger
from app.utils.security import generate_request_id

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = generate_request_id()
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            processing_time = (time.time() - start_time) * 1000
            logger.error(
                "Request failed with exception",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error=str(e),
                processing_time_ms=processing_time
            )
            raise
        
        # Log response
        processing_time = (time.time() - start_time) * 1000
        await self._log_response(request, response, request_id, processing_time)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request"""
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get API key (first 10 chars for security)
        auth_header = request.headers.get("authorization", "")
        api_key_prefix = ""
        if auth_header.startswith("Bearer "):
            api_key_prefix = auth_header[7:17]
        
        logger.info(
            "Request received",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=client_ip,
            user_agent=user_agent,
            api_key_prefix=api_key_prefix,
            content_length=request.headers.get("content-length", 0)
        )
    
    async def _log_response(self, request: Request, response: Response, request_id: str, processing_time: float):
        """Log outgoing response"""
        
        logger.info(
            "Request completed",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            processing_time_ms=processing_time,
            response_size=len(response.body) if hasattr(response, 'body') else 0
        )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Add request context
        if not hasattr(request.state, 'request_id'):
            request.state.request_id = generate_request_id()
        
        request.state.start_time = time.time()
        
        response = await call_next(request)
        return response