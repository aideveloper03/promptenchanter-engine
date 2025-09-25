"""
User authentication middleware for API endpoints
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple
import json
from datetime import datetime

from app.database.database import get_db_session
from app.database.models import User, APIUsageLog
from app.services.user_service import user_service
from app.utils.logger import get_logger
from app.security.encryption import ip_security_manager

logger = get_logger(__name__)


class UserAuthenticationMiddleware:
    """Middleware for user authentication and API usage tracking"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    async def authenticate_api_key(
        self, 
        session: AsyncSession, 
        api_key: str,
        request: Request
    ) -> Tuple[Optional[User], bool]:
        """
        Authenticate API key and check conversation limits
        Returns (user, has_credits)
        """
        
        # Validate API key format
        if not api_key or not api_key.startswith("pe-"):
            return None, False
        
        # Get user by API key
        user = await user_service.validate_api_key(session, api_key)
        
        if not user:
            return None, False
        
        # Check if user has conversation credits
        credits = user.credits or {"main": 0, "reset": 0}
        conversation_limit = user.limits.get("conversation_limit", 0) if user.limits else 0
        
        has_credits = conversation_limit > 0
        
        # Log API usage
        await self._log_api_usage(
            session, user, request, 
            tokens_used=0,  # Will be updated later
            status_code=200  # Will be updated later
        )
        
        return user, has_credits
    
    async def deduct_conversation_credit(
        self,
        session: AsyncSession,
        user: User,
        tokens_used: int = 1
    ) -> bool:
        """
        Deduct conversation credit from user
        Returns True if successful, False if insufficient credits
        """
        
        try:
            # Get current limits
            limits = user.limits or {"conversation_limit": 0, "reset": 0}
            conversation_limit = limits.get("conversation_limit", 0)
            
            if conversation_limit <= 0:
                return False
            
            # Deduct credit
            limits["conversation_limit"] = conversation_limit - 1
            user.limits = limits
            
            # Update last activity
            user.last_activity = datetime.now()
            
            await session.commit()
            
            logger.info(f"Deducted 1 conversation credit from user {user.username}. Remaining: {limits['conversation_limit']}")
            
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to deduct conversation credit for user {user.username}: {e}")
            return False
    
    async def _log_api_usage(
        self,
        session: AsyncSession,
        user: User,
        request: Request,
        tokens_used: int = 0,
        status_code: int = 200,
        response_time_ms: int = 0
    ):
        """Log API usage for monitoring and analytics"""
        
        try:
            client_ip = ip_security_manager.get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "")
            
            # Get date for aggregation
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            usage_log = APIUsageLog(
                user_id=user.id,
                api_key=user.api_key,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                tokens_used=tokens_used,
                ip_address=client_ip,
                user_agent=user_agent,
                date=date_str
            )
            
            session.add(usage_log)
            await session.flush()  # Don't commit here, let caller handle it
            
        except Exception as e:
            logger.error(f"Failed to log API usage: {e}")


# Dependency for API authentication
async def authenticate_api_user(
    request: Request,
    session: AsyncSession = None
) -> User:
    """
    Dependency to authenticate API user and check conversation limits
    """
    
    if session is None:
        async for db_session in get_db_session():
            return await _authenticate_api_user_impl(request, db_session)
    else:
        return await _authenticate_api_user_impl(request, session)


async def _authenticate_api_user_impl(request: Request, session: AsyncSession) -> User:
    """Implementation of API user authentication"""
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authorization header required"}
        )
    
    # Extract API key
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid authorization format. Use 'Bearer <api_key>'"}
        )
    
    api_key = auth_header[7:]  # Remove "Bearer " prefix
    
    # Authenticate
    auth_middleware = UserAuthenticationMiddleware()
    user, has_credits = await auth_middleware.authenticate_api_key(session, api_key, request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid API key"}
        )
    
    if not has_credits:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Insufficient conversation credits",
                "error_code": "CREDITS_EXHAUSTED",
                "limits": user.limits
            }
        )
    
    # Store user in request state for later use
    request.state.authenticated_user = user
    
    return user


# Dependency for API authentication without credit check (for admin endpoints)
async def authenticate_api_user_no_credit_check(
    request: Request,
    session: AsyncSession = None
) -> User:
    """
    Dependency to authenticate API user without checking conversation limits
    """
    
    if session is None:
        async for db_session in get_db_session():
            return await _authenticate_api_user_no_credit_check_impl(request, db_session)
    else:
        return await _authenticate_api_user_no_credit_check_impl(request, session)


async def _authenticate_api_user_no_credit_check_impl(request: Request, session: AsyncSession) -> User:
    """Implementation of API user authentication without credit check"""
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authorization header required"}
        )
    
    # Extract API key
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid authorization format. Use 'Bearer <api_key>'"}
        )
    
    api_key = auth_header[7:]  # Remove "Bearer " prefix
    
    # Authenticate
    user = await user_service.validate_api_key(session, api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid API key"}
        )
    
    # Store user in request state for later use
    request.state.authenticated_user = user
    
    return user


# Global middleware instance
user_auth_middleware = UserAuthenticationMiddleware()