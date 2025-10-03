"""
Email verification endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.services.email_service import email_service
from app.services.mongodb_user_service import mongodb_user_service
from app.database.mongodb import get_mongodb_collection
from app.api.middleware.comprehensive_auth import get_current_user_mongodb
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()
settings = get_settings()

router = APIRouter()


class SendVerificationRequest(BaseModel):
    """Request model for sending verification email"""
    pass


class VerifyEmailRequest(BaseModel):
    """Request model for email verification"""
    otp_code: str


class ResendVerificationRequest(BaseModel):
    """Request model for resending verification email"""
    pass


class VerificationResponse(BaseModel):
    """Response model for verification operations"""
    success: bool
    message: str
    expires_at: Optional[str] = None


@router.post(
    "/send-verification",
    response_model=VerificationResponse,
    summary="Send email verification",
    description="Send verification email to current user"
)
async def send_verification_email(
    request: SendVerificationRequest,
    current_user = Depends(get_current_user_mongodb)
):
    """Send verification email to current user"""
    
    if not settings.email_verification_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Email verification is disabled"}
        )
    
    # Check if user is already verified
    if current_user.get("is_verified", False):
        return VerificationResponse(
            success=False,
            message="Email is already verified"
        )
    
    try:
        result = await email_service.send_verification_email(
            user_id=current_user["_id"],
            email=current_user["email"],
            name=current_user["name"]
        )
        
        return VerificationResponse(
            success=result["success"],
            message=result["message"],
            expires_at=result.get("expires_at")
        )
        
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to send verification email"}
        )


@router.post(
    "/verify",
    response_model=VerificationResponse,
    summary="Verify email with OTP",
    description="Verify email address using OTP code"
)
async def verify_email(
    request: VerifyEmailRequest,
    current_user = Depends(get_current_user_mongodb)
):
    """Verify email using OTP code"""
    
    if not settings.email_verification_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Email verification is disabled"}
        )
    
    # Check if user is already verified
    if current_user.get("is_verified", False):
        return VerificationResponse(
            success=False,
            message="Email is already verified"
        )
    
    try:
        result = await email_service.verify_email_otp(
            user_id=current_user["_id"],
            email=current_user["email"],
            otp_code=request.otp_code
        )
        
        return VerificationResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Email verification failed"}
        )


@router.post(
    "/resend",
    response_model=VerificationResponse,
    summary="Resend verification email",
    description="Resend verification email with rate limiting"
)
async def resend_verification_email(
    request: ResendVerificationRequest,
    current_user = Depends(get_current_user_mongodb)
):
    """Resend verification email with rate limiting"""
    
    if not settings.email_verification_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Email verification is disabled"}
        )
    
    # Check if user is already verified
    if current_user.get("is_verified", False):
        return VerificationResponse(
            success=False,
            message="Email is already verified"
        )
    
    try:
        result = await email_service.resend_verification_email(
            user_id=current_user["_id"],
            email=current_user["email"],
            name=current_user["name"]
        )
        
        return VerificationResponse(
            success=result["success"],
            message=result["message"],
            expires_at=result.get("expires_at")
        )
        
    except Exception as e:
        logger.error(f"Failed to resend verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to resend verification email"}
        )


@router.get(
    "/status",
    response_model=dict,
    summary="Get verification status",
    description="Get current user's email verification status"
)
async def get_verification_status(
    current_user = Depends(get_current_user_mongodb)
):
    """Get user's email verification status"""
    
    return {
        "success": True,
        "is_verified": current_user.get("is_verified", False),
        "email": current_user["email"],
        "verification_enabled": settings.email_verification_enabled,
        "verification_required_for_api": settings.email_verification_enabled
    }