"""
Support staff endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.database import get_db_session
from app.database.models import SupportStaff, User, Admin
from app.models.user_schemas import (
    SupportStaffLoginRequest,
    SupportStaffLoginResponse,
    CreateSupportStaffRequest,
    SupportStaffInfo,
    UpdateUserRequest,
    UserProfile,
    SuccessResponse,
    ErrorResponse
)
from app.services.support_staff_service import support_staff_service
from app.services.admin_service import admin_service
from app.security.encryption import ip_security_manager
from app.security.firewall import firewall_manager
from app.utils.logger import get_logger
from app.api.middleware.comprehensive_auth import get_current_support_staff, get_current_admin

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter()




def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(staff: SupportStaff = Depends(get_current_support_staff)):
        if not support_staff_service.check_permission(staff, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": f"Permission required: {permission}"}
            )
        return staff
    return decorator


@router.post(
    "/login",
    response_model=SupportStaffLoginResponse,
    summary="Support staff login",
    description="Authenticate support staff and create session"
)
async def support_staff_login(
    request: SupportStaffLoginRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Support staff login endpoint"""
    
    # Get client info
    client_ip = ip_security_manager.get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "")
    
    try:
        result = await support_staff_service.authenticate_support_staff(
            session=session,
            username=request.username,
            password=request.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return SupportStaffLoginResponse(**result)
        
    except HTTPException:
        # Record failed attempt for potential abuse monitoring
        await firewall_manager.record_failed_attempt(client_ip, "support_login_failed")
        raise


@router.post(
    "/create",
    response_model=SuccessResponse,
    summary="Create support staff",
    description="Create a new support staff member (admin only)"
)
async def create_support_staff(
    request: CreateSupportStaffRequest,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Create new support staff member (requires admin authentication)"""
    
    result = await support_staff_service.create_support_staff(
        session=session,
        username=request.username,
        name=request.name,
        email=request.email,
        password=request.password,
        staff_level=request.staff_level,
        created_by=current_admin.username
    )
    
    return SuccessResponse(**result)


@router.get(
    "/profile",
    response_model=SupportStaffInfo,
    summary="Get support staff profile",
    description="Get current support staff profile information"
)
async def get_support_staff_profile(
    current_staff: SupportStaff = Depends(get_current_support_staff)
):
    """Get support staff profile"""
    
    return SupportStaffInfo(
        id=current_staff.id,
        username=current_staff.username,
        name=current_staff.name,
        email=current_staff.email,
        staff_level=current_staff.staff_level,
        is_active=current_staff.is_active,
        time_created=current_staff.time_created,
        created_by=current_staff.created_by,
        last_login=current_staff.last_login
    )


@router.get(
    "/permissions",
    response_model=dict,
    summary="Get permissions",
    description="Get current support staff permissions"
)
async def get_support_staff_permissions(
    current_staff: SupportStaff = Depends(get_current_support_staff)
):
    """Get support staff permissions"""
    
    permissions = support_staff_service.staff_permissions.get(current_staff.staff_level, {})
    
    return {
        "staff_level": current_staff.staff_level,
        "permissions": permissions
    }


@router.get(
    "/users",
    response_model=dict,
    summary="Get users list (support staff)",
    description="Get paginated list of users (support staff view)"
)
async def get_users_support(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    current_staff: SupportStaff = Depends(require_permission("can_view_users")),
    session: AsyncSession = Depends(get_db_session)
):
    """Get users list for support staff"""
    
    result = await admin_service.get_users_list(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        user_type=user_type,
        is_active=is_active,
        is_verified=is_verified
    )
    
    # Convert users to limited profile objects (hide sensitive data based on staff level)
    user_profiles = []
    for user in result["users"]:
        user_data = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "user_type": user.user_type,
            "time_created": user.time_created,
            "subscription_plan": user.subscription_plan,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "last_login": user.last_login,
            "last_activity": user.last_activity
        }
        
        # Add additional fields based on staff level
        if current_staff.staff_level in ["support", "advanced"]:
            user_data.update({
                "credits": user.credits,
                "limits": user.limits,
                "level": user.level
            })
        
        if current_staff.staff_level == "advanced":
            user_data.update({
                "about_me": user.about_me,
                "hobbies": user.hobbies,
                "access_rtype": user.access_rtype,
                "additional_notes": user.additional_notes
            })
        
        user_profiles.append(user_data)
    
    return {
        "users": user_profiles,
        "total_count": result["total_count"],
        "page": result["page"],
        "page_size": result["page_size"],
        "staff_level": current_staff.staff_level
    }


@router.get(
    "/users/{user_id}",
    response_model=dict,
    summary="Get user details (support staff)",
    description="Get detailed information about a specific user"
)
async def get_user_details_support(
    user_id: int,
    current_staff: SupportStaff = Depends(require_permission("can_view_users")),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user details for support staff"""
    
    from sqlalchemy import select
    
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "User not found"}
        )
    
    # Build user data based on staff level
    user_data = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "user_type": user.user_type,
        "time_created": user.time_created,
        "subscription_plan": user.subscription_plan,
        "is_verified": user.is_verified,
        "is_active": user.is_active,
        "last_login": user.last_login,
        "last_activity": user.last_activity
    }
    
    # Add additional fields based on staff level
    if current_staff.staff_level in ["support", "advanced"]:
        user_data.update({
            "credits": user.credits,
            "limits": user.limits,
            "level": user.level
        })
    
    if current_staff.staff_level == "advanced":
        user_data.update({
            "about_me": user.about_me,
            "hobbies": user.hobbies,
            "access_rtype": user.access_rtype,
            "additional_notes": user.additional_notes
        })
    
    return {
        "user": user_data,
        "staff_level": current_staff.staff_level,
        "permissions": support_staff_service.staff_permissions.get(current_staff.staff_level, {})
    }


@router.put(
    "/users/{user_id}",
    response_model=SuccessResponse,
    summary="Update user (support staff)",
    description="Update user information with support staff permissions"
)
async def update_user_support(
    user_id: int,
    request: UpdateUserRequest,
    current_staff: SupportStaff = Depends(require_permission("can_update_users")),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user information with support staff permissions"""
    
    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    result = await support_staff_service.update_user_limited(
        session=session,
        staff=current_staff,
        user_id=user_id,
        updates=updates
    )
    
    return SuccessResponse(**result)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=SuccessResponse,
    summary="Reset user password (support staff)",
    description="Reset user password (support level and above)"
)
async def reset_user_password_support(
    user_id: int,
    new_password: str,
    current_staff: SupportStaff = Depends(require_permission("can_reset_passwords")),
    session: AsyncSession = Depends(get_db_session)
):
    """Reset user password"""
    
    result = await support_staff_service.update_user_limited(
        session=session,
        staff=current_staff,
        user_id=user_id,
        updates={"password": new_password}
    )
    
    return SuccessResponse(
        message="Password reset successfully",
        data={"updated_fields": result.get("updated_fields", [])}
    )


@router.put(
    "/users/{user_id}/credits",
    response_model=SuccessResponse,
    summary="Update user credits (support staff)",
    description="Update user conversation credits (support level and above)"
)
async def update_user_credits_support(
    user_id: int,
    credits: dict,
    limits: dict,
    current_staff: SupportStaff = Depends(require_permission("can_update_credits")),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user credits and limits"""
    
    result = await support_staff_service.update_user_limited(
        session=session,
        staff=current_staff,
        user_id=user_id,
        updates={
            "credits": credits,
            "limits": limits
        }
    )
    
    return SuccessResponse(
        message="Credits updated successfully",
        data={"updated_fields": result.get("updated_fields", [])}
    )


@router.put(
    "/users/{user_id}/plan",
    response_model=SuccessResponse,
    summary="Update user subscription plan (support staff)",
    description="Update user subscription plan (support level and above)"
)
async def update_user_plan_support(
    user_id: int,
    subscription_plan: str,
    current_staff: SupportStaff = Depends(require_permission("can_update_plans")),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user subscription plan"""
    
    result = await support_staff_service.update_user_limited(
        session=session,
        staff=current_staff,
        user_id=user_id,
        updates={"subscription_plan": subscription_plan}
    )
    
    return SuccessResponse(
        message="Subscription plan updated successfully",
        data={"updated_fields": result.get("updated_fields", [])}
    )