"""
Support Staff API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
import logging

from app.models.user_schemas import (
    AdminLoginRequest, StandardResponse
)
from app.services.support_service import support_service
from app.security.firewall import firewall
from app.security.encryption import security_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support Staff"])
security = HTTPBearer()


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


async def get_current_support_staff(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated support staff from JWT token"""
    try:
        # Verify JWT token
        payload = security_manager.verify_jwt_token(credentials.credentials)
        if not payload or payload.get('user_type') != 'support':
            raise HTTPException(status_code=401, detail="Support staff authentication required")
        
        # Validate session
        session = support_service.db.validate_session(payload.get('session_id', ''))
        if not session:
            raise HTTPException(status_code=401, detail="Support session expired")
        
        return payload
        
    except Exception as e:
        logger.error(f"Support authentication error: {e}")
        raise HTTPException(status_code=401, detail="Support authentication failed")


@router.post("/login")
async def support_login(request: AdminLoginRequest, http_request: Request):
    """Support staff login"""
    client_ip = get_client_ip(http_request)
    
    # Check firewall
    allowed, reason = firewall.is_ip_allowed(client_ip)
    if not allowed:
        firewall.record_security_event(
            client_ip, "blocked_support_login", "high",
            f"Support login blocked: {reason}"
        )
        raise HTTPException(status_code=403, detail=f"Access denied: {reason}")
    
    try:
        success, message, data = await support_service.support_login(request, client_ip)
        
        if success:
            return {
                "success": True,
                "message": message,
                "access_token": data['access_token'],
                "session_id": data['session_id'],
                "staff_info": data['staff_info']
            }
        else:
            # Record failed support login attempt
            firewall.record_security_event(
                client_ip, "failed_support_login", "medium",
                f"Failed support login attempt: {message}"
            )
            raise HTTPException(status_code=401, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Support login endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Search users by username, email, or name"""
    try:
        users = await support_service.search_users(q, current_staff['staff_level'], limit)
        
        return {
            "success": True,
            "data": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"Search users error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{username}")
async def get_user_info(
    username: str,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Get user information based on staff level permissions"""
    try:
        user = await support_service.get_user_info(username, current_staff['staff_level'])
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found or insufficient permissions")
        
        return {
            "success": True,
            "data": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{username}/activity")
async def get_user_activity(
    username: str,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Get user activity summary"""
    try:
        activity = await support_service.get_user_activity_summary(username, current_staff['staff_level'])
        
        if not activity:
            raise HTTPException(status_code=404, detail="User not found or insufficient permissions")
        
        return {
            "success": True,
            "data": activity
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user activity error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{username}/email", response_model=StandardResponse)
async def update_user_email(
    username: str,
    new_email: str,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Update user email (support level and above)"""
    try:
        success, message = await support_service.update_user_email(
            username, new_email, current_staff['staff_level']
        )
        
        if success:
            # Log support action
            firewall.record_security_event(
                "", "support_email_update", "low",
                f"Support staff {current_staff['username']} updated email for user {username}"
            )
            return StandardResponse(success=True, message=message)
        else:
            if "permissions" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user email error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{username}/password", response_model=StandardResponse)
async def reset_user_password(
    username: str,
    new_password: str,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Reset user password (support level and above)"""
    try:
        success, message = await support_service.reset_user_password(
            username, new_password, current_staff['staff_level']
        )
        
        if success:
            # Log support action
            firewall.record_security_event(
                "", "support_password_reset", "medium",
                f"Support staff {current_staff['username']} reset password for user {username}"
            )
            return StandardResponse(success=True, message=message)
        else:
            if "permissions" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset user password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{username}/limits", response_model=StandardResponse)
async def update_user_limits(
    username: str,
    conversation_limit: Optional[int] = None,
    reset_limit: Optional[int] = None,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Update user conversation limits (support level and above)"""
    try:
        limits_update = {}
        if conversation_limit is not None:
            limits_update['conversation_limit'] = conversation_limit
        if reset_limit is not None:
            limits_update['reset'] = reset_limit
        
        if not limits_update:
            raise HTTPException(status_code=400, detail="No limits provided to update")
        
        success, message = await support_service.update_user_limits(
            username, limits_update, current_staff['staff_level']
        )
        
        if success:
            # Log support action
            firewall.record_security_event(
                "", "support_limits_update", "low",
                f"Support staff {current_staff['username']} updated limits for user {username}"
            )
            return StandardResponse(success=True, message=message)
        else:
            if "permissions" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user limits error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{username}/plan", response_model=StandardResponse)
async def update_user_plan(
    username: str,
    new_plan: str,
    current_staff: Dict[str, Any] = Depends(get_current_support_staff)
):
    """Update user subscription plan (support level and above)"""
    try:
        # Validate plan
        valid_plans = ["free", "basic", "premium", "enterprise"]
        if new_plan not in valid_plans:
            raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {valid_plans}")
        
        success, message = await support_service.update_user_plan(
            username, new_plan, current_staff['staff_level']
        )
        
        if success:
            # Log support action
            firewall.record_security_event(
                "", "support_plan_update", "low",
                f"Support staff {current_staff['username']} updated plan for user {username} to {new_plan}"
            )
            return StandardResponse(success=True, message=message)
        else:
            if "permissions" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user plan error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout", response_model=StandardResponse)
async def support_logout(current_staff: Dict[str, Any] = Depends(get_current_support_staff)):
    """Support staff logout"""
    try:
        # Invalidate session
        with support_service.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
                (current_staff.get('session_id', ''),)
            )
        
        return StandardResponse(
            success=True,
            message="Support staff logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Support logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/permissions")
async def get_my_permissions(current_staff: Dict[str, Any] = Depends(get_current_support_staff)):
    """Get current staff member's permissions"""
    try:
        staff_level = current_staff['staff_level']
        
        permissions = {
            'new': {
                'can_read_user_info': True,
                'can_update_email': False,
                'can_update_password': False,
                'can_update_limits': False,
                'can_update_plan': False,
                'can_view_sensitive_data': False
            },
            'support': {
                'can_read_user_info': True,
                'can_update_email': True,
                'can_update_password': True,
                'can_update_limits': True,
                'can_update_plan': True,
                'can_view_sensitive_data': False
            },
            'advanced': {
                'can_read_user_info': True,
                'can_update_email': True,
                'can_update_password': True,
                'can_update_limits': True,
                'can_update_plan': True,
                'can_view_sensitive_data': True
            }
        }
        
        return {
            "success": True,
            "data": {
                "staff_level": staff_level,
                "permissions": permissions.get(staff_level, permissions['new'])
            }
        }
        
    except Exception as e:
        logger.error(f"Get permissions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")