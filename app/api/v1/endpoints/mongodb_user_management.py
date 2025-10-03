"""
MongoDB-based user management endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.user_schemas import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserLoginRequest,
    UserLoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    APIKeyResponse,
    RegenerateAPIKeyResponse,
    UserProfile,
    UpdateProfileRequest,
    UpdateEmailRequest,
    ResetPasswordRequest,
    DeleteAccountRequest,
    SuccessResponse,
    ErrorResponse
)
from app.services.mongodb_user_service import mongodb_user_service
from app.security.encryption import encryption_manager, ip_security_manager
from app.security.firewall import firewall_manager
from app.utils.logger import get_logger
from app.api.middleware.comprehensive_auth import get_current_user_mongodb, get_current_user_api_mongodb
from app.config.settings import get_settings
from app.database.mongodb import get_mongodb_collection

logger = get_logger(__name__)
security = HTTPBearer()
settings = get_settings()

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account with validation and security measures"
)
async def register_user(
    request: UserRegistrationRequest,
    http_request: Request
):
    """Register a new user"""
    
    # Check if user registration is enabled
    if not settings.user_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "User registration is currently disabled"}
        )
    
    # Get client IP
    client_ip = ip_security_manager.get_client_ip(http_request)
    
    try:
        result = await mongodb_user_service.register_user(
            username=request.username,
            name=request.name,
            email=request.email,
            password=request.password,
            user_type=request.user_type,
            about_me=request.about_me,
            hobbies=request.hobbies,
            ip_address=client_ip
        )
        
        return UserRegistrationResponse(**result)
        
    except HTTPException:
        # Record failed attempt for potential abuse monitoring
        await firewall_manager.record_failed_attempt(client_ip, "registration_failed")
        raise


@router.post(
    "/login",
    response_model=UserLoginResponse,
    summary="User login",
    description="Authenticate user and create session"
)
async def login_user(
    request: UserLoginRequest,
    http_request: Request
):
    """Login user and create session"""
    
    # Get client info
    client_ip = ip_security_manager.get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "")
    
    try:
        result = await mongodb_user_service.authenticate_user(
            email=request.email,
            password=request.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Record successful attempt
        await firewall_manager.record_successful_attempt(client_ip)
        
        return UserLoginResponse(**result)
        
    except HTTPException:
        # Record failed attempt
        await firewall_manager.record_failed_attempt(client_ip, "login_failed")
        raise


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="User logout",
    description="Logout user and invalidate session"
)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user"""
    
    try:
        token = credentials.credentials
        
        # Invalidate session in MongoDB
        sessions_collection = await get_mongodb_collection('user_sessions')
        await sessions_collection.update_one(
            {"session_token": token},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        
        return SuccessResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Logout failed"}
        )


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="Get user profile",
    description="Get current user's profile information"
)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Get user profile"""
    
    return UserProfile(
        id=current_user["_id"],
        username=current_user["username"],
        name=current_user["name"],
        email=current_user["email"],
        about_me=current_user.get("about_me", ""),
        hobbies=current_user.get("hobbies", ""),
        user_type=current_user["user_type"],
        time_created=current_user["time_created"],
        subscription_plan=current_user["subscription_plan"],
        credits=current_user.get("credits", {"main": 0, "reset": 0}),
        limits=current_user.get("limits", {"conversation_limit": 0, "reset": 0}),
        access_rtype=current_user.get("access_rtype", []),
        level=current_user["level"],
        additional_notes=current_user.get("additional_notes", ""),
        is_verified=current_user.get("is_verified", False),
        last_login=current_user.get("last_login"),
        last_activity=current_user.get("last_activity")
    )


@router.put(
    "/profile",
    response_model=SuccessResponse,
    summary="Update user profile",
    description="Update user profile information"
)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Update user profile"""
    
    try:
        users_collection = await get_mongodb_collection('users')
        
        # Prepare update data
        update_data = {"updated_at": datetime.now()}
        
        if request.name is not None:
            update_data["name"] = request.name
        if request.about_me is not None:
            update_data["about_me"] = request.about_me
        if request.hobbies is not None:
            update_data["hobbies"] = request.hobbies
        
        # Update user
        await users_collection.update_one(
            {"_id": current_user["_id"]},
            {"$set": update_data}
        )
        
        logger.info(f"Profile updated for user: {current_user['username']}")
        
        return SuccessResponse(
            message="Profile updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Profile update failed for {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Profile update failed"}
        )


@router.get(
    "/api-key",
    response_model=APIKeyResponse,
    summary="Get API key",
    description="Get user's API key (requires email verification if enabled)"
)
async def get_api_key(
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Get user's API key"""
    
    try:
        result = await mongodb_user_service.get_api_key(current_user["_id"])
        
        return APIKeyResponse(
            success=result["success"],
            message=result["message"],
            api_key=result["api_key"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve API key"}
        )


@router.post(
    "/api-key/regenerate",
    response_model=RegenerateAPIKeyResponse,
    summary="Regenerate API key",
    description="Regenerate user's API key (requires email verification if enabled)"
)
async def regenerate_api_key(
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Regenerate user's API key"""
    
    result = await mongodb_user_service.regenerate_api_key(current_user["_id"])
    
    return RegenerateAPIKeyResponse(**result)


@router.put(
    "/email",
    response_model=SuccessResponse,
    summary="Update email address",
    description="Update user's email address with password verification"
)
async def update_email(
    request: UpdateEmailRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Update user's email address"""
    
    try:
        from app.security.encryption import password_manager
        
        # Verify current password
        if not password_manager.verify_password(request.current_password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid current password"}
            )
        
        # Check if new email already exists
        users_collection = await get_mongodb_collection('users')
        existing_user = await users_collection.find_one({"email": request.new_email.lower()})
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Email already exists"}
            )
        
        # Update email
        update_data = {
            "email": request.new_email.lower(),
            "updated_at": datetime.now()
        }
        
        # Require re-verification if email verification is enabled
        if settings.email_verification_enabled:
            update_data["is_verified"] = False
        
        await users_collection.update_one(
            {"_id": current_user["_id"]},
            {"$set": update_data}
        )
        
        logger.info(f"Email updated for user: {current_user['username']}")
        
        message = "Email updated successfully."
        if settings.email_verification_enabled:
            message += " Please verify your new email address."
        
        return SuccessResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email update failed for {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Email update failed"}
        )


@router.put(
    "/password",
    response_model=SuccessResponse,
    summary="Reset password",
    description="Reset user's password with current password verification"
)
async def reset_password(
    request: ResetPasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Reset user's password"""
    
    try:
        from app.security.encryption import password_manager
        
        # Verify current password
        if not password_manager.verify_password(request.current_password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid current password"}
            )
        
        # Validate new password strength
        is_strong, errors = password_manager.validate_password_strength(request.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Password does not meet requirements", "errors": errors}
            )
        
        # Update password
        users_collection = await get_mongodb_collection('users')
        await users_collection.update_one(
            {"_id": current_user["_id"]},
            {"$set": {
                "password_hash": password_manager.hash_password(request.new_password),
                "failed_login_attempts": 0,
                "locked_until": None,
                "updated_at": datetime.now()
            }}
        )
        
        logger.info(f"Password reset for user: {current_user['username']}")
        
        return SuccessResponse(
            message="Password reset successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed for {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Password reset failed"}
        )


@router.delete(
    "/account",
    response_model=SuccessResponse,
    summary="Delete account",
    description="Delete user account with data archiving"
)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_mongodb)
):
    """Delete user account"""
    
    try:
        from app.security.encryption import password_manager
        
        # Verify password
        if not password_manager.verify_password(request.password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid password"}
            )
        
        # Archive user data
        deleted_users_collection = await get_mongodb_collection('deleted_users')
        deleted_user_doc = {
            "_id": f"deleted_{current_user['_id']}",
            "original_user_id": current_user["_id"],
            "username": current_user["username"],
            "name": current_user["name"],
            "email": current_user["email"],
            "user_type": current_user["user_type"],
            "time_created": current_user["time_created"],
            "subscription_plan": current_user["subscription_plan"],
            "deletion_reason": request.reason,
            "deleted_at": datetime.now(),
            "deleted_by": "self"
        }
        
        await deleted_users_collection.insert_one(deleted_user_doc)
        
        # Delete user and related data
        users_collection = await get_mongodb_collection('users')
        sessions_collection = await get_mongodb_collection('user_sessions')
        messages_collection = await get_mongodb_collection('message_logs')
        
        # Delete in order: sessions, messages, then user
        await sessions_collection.delete_many({"user_id": current_user["_id"]})
        await messages_collection.delete_many({"user_id": current_user["_id"]})
        await users_collection.delete_one({"_id": current_user["_id"]})
        
        logger.info(f"Account deleted for user: {current_user['username']}")
        
        return SuccessResponse(
            message="Account deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed for {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Account deletion failed"}
        )