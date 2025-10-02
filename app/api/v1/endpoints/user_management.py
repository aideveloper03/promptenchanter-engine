"""
User management endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.database import get_db_session
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
from app.services.user_service import user_service
from app.security.encryption import encryption_manager, ip_security_manager
from app.security.firewall import firewall_manager
from app.utils.logger import get_logger
from app.api.middleware.comprehensive_auth import get_current_user_session
from app.config.settings import get_settings

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
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
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
        result = await user_service.register_user(
            session=session,
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
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Login user and create session"""
    
    # Get client info
    client_ip = ip_security_manager.get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "")
    
    try:
        result = await user_service.authenticate_user(
            session=session,
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
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh session",
    description="Refresh session using refresh token"
)
async def refresh_session(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Refresh user session"""
    
    result = await user_service.refresh_session(
        session=session,
        refresh_token=request.refresh_token
    )
    
    return RefreshTokenResponse(**result)


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="User logout",
    description="Logout user and invalidate session"
)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Logout user"""
    
    token = credentials.credentials
    result = await user_service.logout_user(session, token)
    
    return SuccessResponse(**result)


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="Get user profile",
    description="Get current user's profile information"
)
async def get_user_profile(
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user profile"""
    
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        email=current_user.email,
        about_me=current_user.about_me or "",
        hobbies=current_user.hobbies or "",
        user_type=current_user.user_type,
        time_created=current_user.time_created,
        subscription_plan=current_user.subscription_plan,
        credits=current_user.credits or {"main": 0, "reset": 0},
        limits=current_user.limits or {"conversation_limit": 0, "reset": 0},
        access_rtype=current_user.access_rtype or [],
        level=current_user.level,
        additional_notes=current_user.additional_notes or "",
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        last_activity=current_user.last_activity
    )


@router.put(
    "/profile",
    response_model=SuccessResponse,
    summary="Update user profile",
    description="Update user profile information"
)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user profile"""
    
    try:
        # Update fields if provided
        if request.name is not None:
            current_user.name = request.name
        if request.about_me is not None:
            current_user.about_me = request.about_me
        if request.hobbies is not None:
            current_user.hobbies = request.hobbies
        
        await session.commit()
        
        logger.info(f"Profile updated for user: {current_user.username}")
        
        return SuccessResponse(
            message="Profile updated successfully"
        )
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Profile update failed for {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Profile update failed"}
        )


@router.get(
    "/api-key",
    response_model=APIKeyResponse,
    summary="Get API key",
    description="Get user's API key (encrypted for security)"
)
async def get_api_key(
    current_user = Depends(get_current_user_session)
):
    """Get user's API key"""
    
    # Return encrypted API key for security
    encrypted_key = encryption_manager.encrypt(current_user.api_key)
    
    return APIKeyResponse(
        success=True,
        message="API key retrieved successfully",
        api_key=encrypted_key
    )


@router.post(
    "/api-key/regenerate",
    response_model=RegenerateAPIKeyResponse,
    summary="Regenerate API key",
    description="Regenerate user's API key"
)
async def regenerate_api_key(
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Regenerate user's API key"""
    
    result = await user_service.regenerate_api_key(session, current_user.id)
    
    return RegenerateAPIKeyResponse(**result)


@router.put(
    "/email",
    response_model=SuccessResponse,
    summary="Update email address",
    description="Update user's email address with password verification"
)
async def update_email(
    request: UpdateEmailRequest,
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user's email address"""
    
    try:
        # Verify current password
        from app.security.encryption import password_manager
        
        if not password_manager.verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid current password"}
            )
        
        # Check if new email already exists
        from sqlalchemy import select
        from app.database.models import User
        
        result = await session.execute(
            select(User).where(User.email == request.new_email.lower())
        )
        
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Email already exists"}
            )
        
        # Update email (requires verification if enabled)
        current_user.email = request.new_email.lower()
        if settings.email_verification_enabled:
            current_user.is_verified = False  # Require re-verification
        
        await session.commit()
        
        logger.info(f"Email updated for user: {current_user.username}")
        
        message = "Email updated successfully."
        if settings.email_verification_enabled:
            message += " Please verify your new email address."
        
        return SuccessResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Email update failed for {current_user.username}: {e}")
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
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Reset user's password"""
    
    try:
        # Verify current password
        from app.security.encryption import password_manager
        
        if not password_manager.verify_password(request.current_password, current_user.password_hash):
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
        current_user.password_hash = password_manager.hash_password(request.new_password)
        current_user.failed_login_attempts = 0  # Reset failed attempts
        current_user.locked_until = None  # Remove any locks
        
        await session.commit()
        
        logger.info(f"Password reset for user: {current_user.username}")
        
        return SuccessResponse(
            message="Password reset successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Password reset failed for {current_user.username}: {e}")
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
    current_user = Depends(get_current_user_session),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete user account"""
    
    try:
        # Verify password
        from app.security.encryption import password_manager
        
        if not password_manager.verify_password(request.password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid password"}
            )
        
        # Archive user data
        from app.database.models import DeletedUser
        
        deleted_user = DeletedUser(
            original_user_id=current_user.id,
            username=current_user.username,
            name=current_user.name,
            email=current_user.email,
            user_type=current_user.user_type,
            time_created=current_user.time_created,
            subscription_plan=current_user.subscription_plan,
            deletion_reason=request.reason,
            deleted_by="self"
        )
        
        session.add(deleted_user)
        
        # Delete user (cascades to sessions and messages)
        await session.delete(current_user)
        await session.commit()
        
        logger.info(f"Account deleted for user: {current_user.username}")
        
        return SuccessResponse(
            message="Account deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Account deletion failed for {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Account deletion failed"}
        )