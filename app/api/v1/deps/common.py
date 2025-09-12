"""
Common dependencies for PromptEnchanter API
"""
from fastapi import Request, Depends
from app.utils.logger import RequestLogger
from app.api.middleware.auth import authenticate_api_key
from app.api.middleware.rate_limit import check_rate_limit


async def get_request_logger(request: Request) -> RequestLogger:
    """Get request logger with context"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    endpoint = request.url.path
    return RequestLogger(request_id, endpoint)


async def get_authenticated_request_logger(
    request: Request,
    api_key: str = Depends(authenticate_api_key)
) -> RequestLogger:
    """Get request logger for authenticated requests"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    endpoint = request.url.path
    logger = RequestLogger(request_id, endpoint)
    logger.info("Request authenticated", api_key_prefix=api_key[:10])
    return logger


# Combined dependency for authenticated and rate-limited requests
async def get_secure_request_logger(
    request: Request,
    api_key: str = Depends(authenticate_api_key),
    _: None = Depends(check_rate_limit)
) -> RequestLogger:
    """Get request logger for secure (authenticated + rate limited) requests"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    endpoint = request.url.path
    logger = RequestLogger(request_id, endpoint)
    logger.info("Secure request", api_key_prefix=api_key[:10])
    return logger