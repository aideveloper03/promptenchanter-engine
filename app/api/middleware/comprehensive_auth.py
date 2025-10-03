"""
Comprehensive authentication and authorization middleware for PromptEnchanter
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Union, Tuple, Dict, Any
from datetime import datetime
import json

from app.database.database import get_db_session
from app.database.models import User, Admin, SupportStaff, UserSession
from app.services.user_service import user_service
from app.services.mongodb_user_service import mongodb_user_service
from app.services.admin_service import admin_service
from app.services.support_staff_service import support_staff_service
from app.utils.logger import get_logger
from app.security.encryption import ip_security_manager
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": message}
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": message}
        )


class ComprehensiveAuthMiddleware:
    """Comprehensive authentication and authorization middleware"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    async def authenticate_session_token(
        self,
        session: AsyncSession,
        token: str,
        request: Request
    ) -> Optional[Union[User, Admin, SupportStaff]]:
        """Authenticate session token and return user/admin/staff"""
        
        try:
            # Check if it's a user session
            user = await user_service.validate_session(session, token)
            if user:
                # Update last activity
                user.last_activity = datetime.now()
                await session.commit()
                return user
            
            # Check if it's an admin session
            admin = await admin_service.validate_admin_session(session, token)
            if admin:
                return admin
            
            # Check if it's a support staff session
            support_staff = await support_staff_service.validate_support_staff_session(session, token)
            if support_staff:
                return support_staff
            
            return None
            
        except Exception as e:
            logger.error(f"Session authentication failed: {e}")
            return None
    
    async def authenticate_api_key(
        self,
        session: AsyncSession,
        api_key: str,
        request: Request
    ) -> Optional[User]:
        """Authenticate API key and return user"""
        
        try:
            # Validate API key format
            if not api_key or not api_key.startswith("pe-"):
                return None
            
            # Get user by API key
            user = await user_service.validate_api_key(session, api_key)
            
            if user:
                # Update last activity
                user.last_activity = datetime.now()
                await session.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return None
    
    async def check_user_permissions(
        self,
        user: Union[User, Admin, SupportStaff],
        required_permissions: list = None,
        require_admin: bool = False,
        require_super_admin: bool = False,
        require_verified: bool = False
    ) -> bool:
        """Check if user has required permissions"""
        
        try:
            # Check if user is active
            if not user.is_active:
                return False
            
            # Check verification requirement
            if require_verified and hasattr(user, 'is_verified'):
                if not user.is_verified and settings.email_verification_enabled:
                    return False
            
            # Check admin requirements
            if require_super_admin:
                if not isinstance(user, Admin) or not user.is_super_admin:
                    return False
            elif require_admin:
                if not isinstance(user, Admin):
                    return False
            
            # Check specific permissions for admins
            if required_permissions and isinstance(user, Admin):
                user_permissions = user.permissions or []
                if not all(perm in user_permissions for perm in required_permissions):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False


# Global middleware instance
auth_middleware = ComprehensiveAuthMiddleware()


# Dependency functions for different authentication types

async def get_current_user_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    request: Request = None
) -> User:
    """Get current user from session token"""
    
    if not credentials:
        raise AuthenticationError("Authentication credentials required")
    
    token = credentials.credentials
    user = await auth_middleware.authenticate_session_token(session, token, request)
    
    if not user or not isinstance(user, User):
        raise AuthenticationError("Invalid or expired session token")
    
    # Check if email verification is required
    if settings.email_verification_enabled and not user.is_verified:
        raise AuthenticationError("Email verification required")
    
    return user


async def get_current_user_api(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    request: Request = None
) -> User:
    """Get current user from API key"""
    
    if not credentials:
        raise AuthenticationError("API key required")
    
    api_key = credentials.credentials
    user = await auth_middleware.authenticate_api_key(session, api_key, request)
    
    if not user:
        raise AuthenticationError("Invalid API key")
    
    # Check if email verification is required
    if settings.email_verification_enabled and not user.is_verified:
        raise AuthenticationError("Email verification required")
    
    return user


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    request: Request = None
) -> Admin:
    """Get current admin from session token"""
    
    if not credentials:
        raise AuthenticationError("Admin authentication required")
    
    token = credentials.credentials
    admin = await admin_service.validate_admin_session(session, token)
    
    if not admin:
        raise AuthenticationError("Invalid or expired admin session token")
    
    return admin


async def get_current_super_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Require super admin privileges"""
    
    if not current_admin.is_super_admin:
        raise AuthorizationError("Super admin privileges required")
    
    return current_admin


async def get_current_support_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    request: Request = None
) -> SupportStaff:
    """Get current support staff from session token"""
    
    if not credentials:
        raise AuthenticationError("Support staff authentication required")
    
    token = credentials.credentials
    support_staff = await support_staff_service.validate_support_staff_session(session, token)
    
    if not support_staff:
        raise AuthenticationError("Invalid or expired support staff session token")
    
    return support_staff


async def get_current_user_or_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    request: Request = None
) -> Union[User, Admin]:
    """Get current user or admin from session token"""
    
    if not credentials:
        raise AuthenticationError("Authentication required")
    
    token = credentials.credentials
    user_or_admin = await auth_middleware.authenticate_session_token(session, token, request)
    
    if not user_or_admin:
        raise AuthenticationError("Invalid or expired session token")
    
    # Check verification for users
    if isinstance(user_or_admin, User):
        if settings.email_verification_enabled and not user_or_admin.is_verified:
            raise AuthenticationError("Email verification required")
    
    return user_or_admin


# Optional authentication (returns None if not authenticated)
async def get_optional_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """Optional user authentication - returns None if not authenticated"""
    
    try:
        # Try to get credentials from request header manually
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token_or_key = auth_header[7:]  # Remove "Bearer " prefix
        
        # Try session token first
        user = await auth_middleware.authenticate_session_token(session, token_or_key, request)
        if user and isinstance(user, User):
            return user
        
        # Try API key
        user = await auth_middleware.authenticate_api_key(session, token_or_key, request)
        if user:
            return user
        
        return None
        
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


# Permission-based dependencies
def require_permissions(permissions: list):
    """Create a dependency that requires specific permissions"""
    
    async def permission_dependency(
        current_admin: Admin = Depends(get_current_admin)
    ) -> Admin:
        if not auth_middleware.check_user_permissions(
            current_admin, 
            required_permissions=permissions
        ):
            raise AuthorizationError(f"Required permissions: {', '.join(permissions)}")
        return current_admin
    
    return permission_dependency


def require_verified_user():
    """Create a dependency that requires verified user"""
    
    async def verified_user_dependency(
        current_user: User = Depends(get_current_user_session)
    ) -> User:
        if settings.email_verification_enabled and not current_user.is_verified:
            raise AuthenticationError("Email verification required")
        return current_user
    
    return verified_user_dependency


# Credit check dependencies
async def get_user_with_credits(
    current_user: User = Depends(get_current_user_api)
) -> User:
    """Get user and check if they have conversation credits"""
    
    limits = current_user.limits or {"conversation_limit": 0, "reset": 0}
    conversation_limit = limits.get("conversation_limit", 0)
    
    if conversation_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Insufficient conversation credits",
                "error_code": "CREDITS_EXHAUSTED",
                "limits": current_user.limits
            }
        )
    
    return current_user


# Rate limiting bypass for admins
async def get_user_bypass_rate_limit(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[Union[User, Admin]]:
    """Get user/admin and check if they can bypass rate limits"""
    
    try:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        
        # Check if it's an admin (admins bypass rate limits)
        admin = await admin_service.validate_admin_session(session, token)
        if admin:
            return admin
        
        # Check if it's a user
        user = await user_service.validate_session(session, token)
        if user:
            return user
        
        return None
        
    except Exception:
        return None


# MongoDB-based authentication functions

async def get_current_user_mongodb(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> Dict[str, Any]:
    """Get current user from MongoDB using session token"""
    
    if not credentials:
        raise AuthenticationError("Authentication credentials required")
    
    token = credentials.credentials
    
    # Try session token authentication
    user = await mongodb_user_service.validate_session(token)
    
    if not user:
        raise AuthenticationError("Invalid or expired session token")
    
    # Check if email verification is required
    if settings.email_verification_enabled and not user.get("is_verified", False):
        raise AuthenticationError("Email verification required")
    
    return user


async def get_current_user_api_mongodb(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> Dict[str, Any]:
    """Get current user from MongoDB using API key"""
    
    if not credentials:
        raise AuthenticationError("API key required")
    
    api_key = credentials.credentials
    user = await mongodb_user_service.validate_api_key(api_key)
    
    if not user:
        raise AuthenticationError("Invalid API key")
    
    # Check if email verification is required for API access
    if settings.email_verification_enabled and not user.get("is_verified", False):
        raise AuthenticationError("Email verification required for API access")
    
    return user


async def get_optional_current_user_mongodb(
    request: Request
) -> Optional[Dict[str, Any]]:
    """Optional MongoDB user authentication - returns None if not authenticated"""
    
    try:
        # Try to get credentials from request header manually
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token_or_key = auth_header[7:]  # Remove "Bearer " prefix
        
        # Try session token first
        user = await mongodb_user_service.validate_session(token_or_key)
        if user:
            return user
        
        # Try API key
        user = await mongodb_user_service.validate_api_key(token_or_key)
        if user:
            return user
        
        return None
        
    except Exception as e:
        logger.debug(f"Optional MongoDB authentication failed: {e}")
        return None