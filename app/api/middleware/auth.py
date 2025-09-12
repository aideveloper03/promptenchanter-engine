"""
Authentication middleware for PromptEnchanter
"""
from typing import Optional
from fastapi import HTTPException, Security, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.security import verify_api_key
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


async def authenticate_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Authenticate API key from Bearer token"""
    
    if not credentials:
        logger.warning("No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_api_key(credentials.credentials):
        logger.warning("Invalid API key provided", api_key_prefix=credentials.credentials[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


# Optional authentication for endpoints that may not require it
async def optional_authenticate_api_key(
    request: Request
) -> Optional[str]:
    """Optional authentication - returns None if no credentials provided"""
    
    # Try to get credentials from request header manually
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    api_key = auth_header[7:]  # Remove "Bearer " prefix
    
    if not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key