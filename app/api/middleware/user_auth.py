"""
Enhanced User Authentication Middleware
"""
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Tuple
import logging
import time

from app.services.user_service import user_service
from app.services.message_logging_service import message_logging_service
from app.security.firewall import firewall

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def authenticate_api_request(request: Request) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Authenticate API request using API key
    Returns: (success, user_data, error_message)
    """
    try:
        # Get client IP
        client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        # Check firewall first
        allowed, reason = firewall.is_ip_allowed(client_ip)
        if not allowed:
            firewall.record_security_event(
                client_ip, "blocked_api_request", "high",
                f"API request blocked: {reason}"
            )
            return False, None, f"Access denied: {reason}"
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False, None, "Missing Authorization header"
        
        # Extract API key
        if not auth_header.startswith("Bearer "):
            return False, None, "Invalid Authorization header format"
        
        api_key = auth_header.split(" ")[1]
        
        # Authenticate API key
        success, user_data, error_message = await user_service.authenticate_api_key(api_key, client_ip)
        
        if success:
            # Store user data in request state
            request.state.user = user_data
            request.state.authenticated = True
            return True, user_data, None
        else:
            return False, None, error_message
            
    except Exception as e:
        logger.error(f"API authentication error: {e}")
        return False, None, "Authentication error"


async def log_api_request(request: Request, response_data: Dict[str, Any], 
                         processing_time_ms: int, tokens_used: int = 0):
    """Log API request and response"""
    try:
        if not hasattr(request.state, 'user') or not request.state.user:
            return
        
        user = request.state.user
        
        # Extract request data
        request_messages = []
        if hasattr(request.state, 'request_data'):
            request_data = request.state.request_data
            if isinstance(request_data, dict):
                messages = request_data.get('messages', [])
                if messages:
                    request_messages = messages
        
        # Combine request and response for logging
        combined_messages = {
            'request': request_messages,
            'response': response_data
        }
        
        # Log the message
        await message_logging_service.log_message(
            username=user['username'],
            email=user['email'],
            model=request_data.get('level', 'unknown') if hasattr(request.state, 'request_data') else 'unknown',
            messages=[combined_messages],
            research_model=request_data.get('ai_research', False) if hasattr(request.state, 'request_data') else False,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"API request logging error: {e}")


class UserAuthMiddleware:
    """Middleware for user authentication and logging"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Check if this is an API endpoint that requires authentication
        path = request.url.path
        
        # Skip authentication for certain paths
        skip_auth_paths = [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/user/register", "/user/login", "/admin/login", "/support/login"
        ]
        
        requires_auth = (
            path.startswith("/v1/chat/") or 
            path.startswith("/v1/batch/") or
            path.startswith("/v1/research/")
        )
        
        if requires_auth and not any(path.startswith(skip) for skip in skip_auth_paths):
            # Authenticate the request
            success, user_data, error_message = await authenticate_api_request(request)
            
            if not success:
                # Return authentication error
                status_code = 429 if "limit exceeded" in error_message.lower() else 401
                response_body = {
                    "error": "authentication_failed",
                    "message": error_message
                }
                
                response = Response(
                    content=json.dumps(response_body),
                    status_code=status_code,
                    headers={"content-type": "application/json"}
                )
                await response(scope, receive, send)
                return
        
        # Continue with the request
        await self.app(scope, receive, send)