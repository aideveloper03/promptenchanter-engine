"""
User Management API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from app.models.user_schemas import (
    UserRegistrationRequest, UserRegistrationResponse,
    UserLoginRequest, UserLoginResponse,
    UserProfile, UserProfileUpdateRequest,
    EmailUpdateRequest, PasswordResetRequest,
    APIKeyResponse, APIKeyRegenerateRequest,
    StandardResponse, ErrorResponse
)
from app.services.user_service import user_service
from app.security.firewall import firewall
from app.security.encryption import security_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["User Management"])
security = HTTPBearer()


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def get_user_agent(request: Request) -> str:
    """Get user agent"""
    return request.headers.get("User-Agent", "")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    try:
        # Verify JWT token
        payload = security_manager.verify_jwt_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Validate session
        session = user_service.db.validate_session(payload.get('session_id', ''))
        if not session:
            raise HTTPException(status_code=401, detail="Session expired")
        
        return payload
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(request: UserRegistrationRequest, http_request: Request):
    """Register a new user"""
    client_ip = get_client_ip(http_request)
    
    # Check firewall
    allowed, reason = firewall.is_ip_allowed(client_ip)
    if not allowed:
        firewall.record_security_event(
            client_ip, "blocked_registration", "high",
            f"Registration blocked: {reason}"
        )
        raise HTTPException(status_code=403, detail=f"Access denied: {reason}")
    
    try:
        success, message, api_key = await user_service.register_user(request, client_ip)
        
        if success:
            return UserRegistrationResponse(
                success=True,
                message=message,
                api_key=api_key,
                user_id=request.username
            )
        else:
            return UserRegistrationResponse(
                success=False,
                message=message
            )
            
    except Exception as e:
        logger.error(f"Registration endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=UserLoginResponse)
async def login_user(request: UserLoginRequest, http_request: Request):
    """Login user"""
    client_ip = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)
    
    # Check firewall
    allowed, reason = firewall.is_ip_allowed(client_ip)
    if not allowed:
        firewall.record_security_event(
            client_ip, "blocked_login", "high",
            f"Login blocked: {reason}"
        )
        raise HTTPException(status_code=403, detail=f"Access denied: {reason}")
    
    try:
        success, message, data = await user_service.login_user(request, client_ip, user_agent)
        
        if success:
            return UserLoginResponse(
                success=True,
                message=message,
                access_token=data['access_token'],
                session_id=data['session_id'],
                user_info=data['user_info']
            )
        else:
            return UserLoginResponse(
                success=False,
                message=message
            )
            
    except Exception as e:
        logger.error(f"Login endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user profile"""
    try:
        profile = await user_service.get_user_profile(current_user['username'])
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserProfile(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/profile", response_model=StandardResponse)
async def update_profile(
    request: UserProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    try:
        success, message = await user_service.update_user_profile(current_user['username'], request)
        
        return StandardResponse(
            success=success,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/change-password", response_model=StandardResponse)
async def change_password(
    request: PasswordResetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change user password"""
    try:
        success, message = await user_service.change_password(current_user['username'], request)
        
        if success:
            return StandardResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api-key", response_model=APIKeyResponse)
async def get_api_key(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get encrypted API key"""
    try:
        success, message, data = await user_service.get_encrypted_api_key(current_user['username'])
        
        if success:
            return APIKeyResponse(
                success=True,
                message=message,
                encrypted_key=data['encrypted_key'],
                key_preview=data['key_preview']
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get API key error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/regenerate-api-key", response_model=APIKeyResponse)
async def regenerate_api_key(
    request: APIKeyRegenerateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Regenerate API key"""
    try:
        success, message, new_key = await user_service.regenerate_api_key(
            current_user['username'], request.current_password
        )
        
        if success:
            # Encrypt the new key for response
            encrypted_key = security_manager.encrypt_api_key(new_key)
            key_preview = f"{new_key[:10]}..."
            
            return APIKeyResponse(
                success=True,
                message=message,
                encrypted_key=encrypted_key,
                key_preview=key_preview
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regenerate API key error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/account", response_model=StandardResponse)
async def delete_account(
    password: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete user account"""
    try:
        success, message = await user_service.delete_user_account(
            current_user['username'], password
        )
        
        if success:
            return StandardResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout", response_model=StandardResponse)
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (invalidate session)"""
    try:
        # Invalidate session
        with user_service.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
                (current_user.get('session_id', ''),)
            )
        
        return StandardResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# API Key Authentication Endpoint (for external API usage)
@router.post("/authenticate", response_model=StandardResponse)
async def authenticate_api_key(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Authenticate API key for external usage"""
    client_ip = get_client_ip(request)
    
    # Check firewall
    allowed, reason = firewall.is_ip_allowed(client_ip)
    if not allowed:
        firewall.record_security_event(
            client_ip, "blocked_api_auth", "high",
            f"API authentication blocked: {reason}"
        )
        raise HTTPException(status_code=403, detail=f"Access denied: {reason}")
    
    try:
        # Extract API key from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        
        api_key = authorization.split(" ")[1]
        
        # Authenticate
        success, user_data, error_message = await user_service.authenticate_api_key(api_key, client_ip)
        
        if success:
            return StandardResponse(
                success=True,
                message="Authentication successful",
                data={
                    'username': user_data['username'],
                    'remaining_limits': user_data['limits']
                }
            )
        else:
            # Return 429 for rate limit exceeded
            if "limit exceeded" in error_message.lower():
                raise HTTPException(status_code=429, detail=error_message)
            else:
                raise HTTPException(status_code=401, detail=error_message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API authentication error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")