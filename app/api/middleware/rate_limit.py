"""
Rate limiting middleware for PromptEnchanter
"""
import time
from typing import Dict, List
from fastapi import HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config.settings import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"]
)


def get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting"""
    
    # Try to get API key from Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
        return f"api_key:{api_key[:10]}"  # Use first 10 chars of API key
    
    # Fallback to IP address
    return get_remote_address(request)


class CustomRateLimiter:
    """Custom rate limiter with burst support"""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str, max_requests: int, window_seconds: int, burst: int = None) -> bool:
        """Check if request is allowed"""
        
        now = time.time()
        window_start = now - window_seconds
        
        # Initialize client if not exists
        if client_id not in self._requests:
            self._requests[client_id] = []
        
        # Clean old requests
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id]
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self._requests[client_id]) >= max_requests:
            return False
        
        # Check burst limit if specified
        if burst:
            recent_requests = [
                req_time for req_time in self._requests[client_id]
                if req_time > now - 60  # Last minute
            ]
            if len(recent_requests) >= burst:
                return False
        
        # Add current request
        self._requests[client_id].append(now)
        return True
    
    def get_reset_time(self, client_id: str, window_seconds: int) -> int:
        """Get time when rate limit resets"""
        
        if client_id not in self._requests or not self._requests[client_id]:
            return int(time.time())
        
        oldest_request = min(self._requests[client_id])
        return int(oldest_request + window_seconds)


# Global rate limiter instance
custom_limiter = CustomRateLimiter()


async def check_rate_limit(request: Request):
    """Check rate limit for request"""
    
    client_id = get_client_id(request)
    
    # Different limits for different endpoints
    endpoint = request.url.path
    
    if "/batch" in endpoint:
        # Stricter limits for batch processing
        max_requests = settings.rate_limit_requests_per_minute // 4
        burst = settings.rate_limit_burst // 2
    else:
        # Standard limits
        max_requests = settings.rate_limit_requests_per_minute
        burst = settings.rate_limit_burst
    
    if not custom_limiter.is_allowed(client_id, max_requests, 60, burst):
        reset_time = custom_limiter.get_reset_time(client_id, 60)
        
        logger.warning(
            "Rate limit exceeded",
            client_id=client_id,
            endpoint=endpoint,
            reset_time=reset_time
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time - int(time.time()))
            }
        )


# Rate limit decorator for specific endpoints
def rate_limit(requests_per_minute: int = None, burst: int = None):
    """Decorator for custom rate limiting"""
    
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            client_id = get_client_id(request)
            
            max_requests = requests_per_minute or settings.rate_limit_requests_per_minute
            burst_limit = burst or settings.rate_limit_burst
            
            if not custom_limiter.is_allowed(client_id, max_requests, 60, burst_limit):
                reset_time = custom_limiter.get_reset_time(client_id, 60)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - int(time.time()))
                    }
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator