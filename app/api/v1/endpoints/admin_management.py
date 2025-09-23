"""
Admin management endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.database import get_db_session
from app.database.models import Admin
from app.models.user_schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    CreateAdminRequest,
    UpdateUserRequest,
    UserListResponse,
    UserProfile,
    UserStatistics,
    APIUsageStatistics,
    SystemHealth,
    SecurityLogResponse,
    MessageLogResponse,
    SuccessResponse,
    ErrorResponse
)
from app.services.admin_service import admin_service
from app.services.user_service import user_service
from app.security.encryption import ip_security_manager
from app.security.firewall import firewall_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> Admin:
    """Get current admin from session token"""
    token = credentials.credentials
    admin = await admin_service.validate_admin_session(session, token)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired admin session token"}
        )
    
    return admin


async def require_super_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Require super admin privileges"""
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Super admin privileges required"}
        )
    
    return current_admin


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Admin login",
    description="Authenticate admin user and create session"
)
async def admin_login(
    request: AdminLoginRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Admin login endpoint"""
    
    # Get client info
    client_ip = ip_security_manager.get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "")
    
    try:
        result = await admin_service.authenticate_admin(
            session=session,
            username=request.username,
            password=request.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return AdminLoginResponse(**result)
        
    except HTTPException:
        # Record failed attempt for potential abuse monitoring
        await firewall_manager.record_failed_attempt(client_ip, "admin_login_failed")
        raise


@router.post(
    "/create-admin",
    response_model=SuccessResponse,
    summary="Create new admin",
    description="Create a new admin user (super admin only)"
)
async def create_admin(
    request: CreateAdminRequest,
    current_admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Create new admin user"""
    
    result = await admin_service.create_admin(
        session=session,
        username=request.username,
        name=request.name,
        email=request.email,
        password=request.password,
        is_super_admin=request.is_super_admin,
        permissions=request.permissions,
        created_by=current_admin.username
    )
    
    return SuccessResponse(**result)


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Get users list",
    description="Get paginated list of users with filtering options"
)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get users list with filtering"""
    
    result = await admin_service.get_users_list(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        user_type=user_type,
        is_active=is_active,
        is_verified=is_verified
    )
    
    # Convert users to UserProfile objects
    user_profiles = []
    for user in result["users"]:
        user_profile = UserProfile(
            id=user.id,
            username=user.username,
            name=user.name,
            email=user.email,
            about_me=user.about_me,
            hobbies=user.hobbies,
            user_type=user.user_type,
            time_created=user.time_created,
            subscription_plan=user.subscription_plan,
            credits=user.credits,
            limits=user.limits,
            access_rtype=user.access_rtype,
            level=user.level,
            additional_notes=user.additional_notes,
            is_verified=user.is_verified,
            last_login=user.last_login,
            last_activity=user.last_activity
        )
        user_profiles.append(user_profile)
    
    return UserListResponse(
        users=user_profiles,
        total_count=result["total_count"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get(
    "/users/{user_id}",
    response_model=UserProfile,
    summary="Get user details",
    description="Get detailed information about a specific user"
)
async def get_user_details(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user details"""
    
    from sqlalchemy import select
    from app.database.models import User
    
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "User not found"}
        )
    
    return UserProfile(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        about_me=user.about_me,
        hobbies=user.hobbies,
        user_type=user.user_type,
        time_created=user.time_created,
        subscription_plan=user.subscription_plan,
        credits=user.credits,
        limits=user.limits,
        access_rtype=user.access_rtype,
        level=user.level,
        additional_notes=user.additional_notes,
        is_verified=user.is_verified,
        last_login=user.last_login,
        last_activity=user.last_activity
    )


@router.put(
    "/users/{user_id}",
    response_model=SuccessResponse,
    summary="Update user",
    description="Update user information"
)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user information"""
    
    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    result = await admin_service.update_user(
        session=session,
        user_id=user_id,
        updates=updates,
        admin_username=current_admin.username
    )
    
    return SuccessResponse(**result)


@router.delete(
    "/users/{user_id}",
    response_model=SuccessResponse,
    summary="Delete user",
    description="Delete user account (super admin only)"
)
async def delete_user(
    user_id: int,
    reason: Optional[str] = Query("Admin deletion"),
    current_admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete user account"""
    
    result = await admin_service.delete_user(
        session=session,
        user_id=user_id,
        admin_username=current_admin.username,
        reason=reason
    )
    
    return SuccessResponse(**result)


@router.post(
    "/users/{user_id}/regenerate-api-key",
    response_model=SuccessResponse,
    summary="Regenerate user API key",
    description="Regenerate API key for a specific user"
)
async def regenerate_user_api_key(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Regenerate API key for user"""
    
    result = await user_service.regenerate_api_key(session, user_id)
    
    # Log admin action
    from app.services.admin_service import admin_service
    await admin_service._log_admin_security_event(
        session, "api_key_regenerated_by_admin",
        username=current_admin.username,
        details={"target_user_id": user_id}
    )
    
    return SuccessResponse(
        message="API key regenerated successfully",
        data={"api_key": result["api_key"]}
    )


@router.get(
    "/statistics",
    response_model=dict,
    summary="Get system statistics",
    description="Get comprehensive system statistics and metrics"
)
async def get_system_statistics(
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system statistics"""
    
    return await admin_service.get_system_statistics(session)


@router.get(
    "/security-logs",
    response_model=SecurityLogResponse,
    summary="Get security logs",
    description="Get security event logs with pagination"
)
async def get_security_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get security logs"""
    
    from sqlalchemy import select, func, and_
    from app.database.models import SecurityLog
    
    # Build query
    query = select(SecurityLog)
    
    if event_type:
        query = query.where(SecurityLog.event_type == event_type)
    if severity:
        query = query.where(SecurityLog.severity == severity)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(SecurityLog.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return SecurityLogResponse(
        logs=logs,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


@router.get(
    "/message-logs/{user_id}",
    response_model=MessageLogResponse,
    summary="Get user message logs",
    description="Get message logs for a specific user"
)
async def get_user_message_logs(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get message logs for a specific user"""
    
    from app.services.message_logging_service import message_logging_service
    
    result = await message_logging_service.get_user_messages(
        session=session,
        user_id=user_id,
        page=page,
        page_size=page_size
    )
    
    return MessageLogResponse(
        logs=result["messages"],
        total_count=result["total_count"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get(
    "/health",
    response_model=SystemHealth,
    summary="System health check",
    description="Get system health status and metrics"
)
async def get_system_health(
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system health status"""
    
    try:
        # Test database connection
        await session.execute(select(1))
        database_connected = True
    except Exception:
        database_connected = False
    
    # Test Redis connection
    from app.utils.cache import cache_manager
    redis_connected = await cache_manager.is_connected()
    
    # Get user count
    from sqlalchemy import func
    from app.database.models import User, UserSession
    
    total_users_result = await session.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    # Get active sessions
    from datetime import datetime
    active_sessions_result = await session.execute(
        select(func.count(UserSession.id)).where(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now()
            )
        )
    )
    active_sessions = active_sessions_result.scalar()
    
    # System load (basic metrics)
    import psutil
    system_load = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
    
    # Calculate uptime (placeholder)
    uptime_seconds = 0.0  # Would need to track actual startup time
    
    status_text = "healthy" if database_connected and redis_connected else "degraded"
    
    return SystemHealth(
        status=status_text,
        database_connected=database_connected,
        redis_connected=redis_connected,
        total_users=total_users,
        active_sessions=active_sessions,
        system_load=system_load,
        uptime_seconds=uptime_seconds
    )