"""
Admin API Endpoints - Enhanced with User Management
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
import logging

from app.models.user_schemas import (
    AdminLoginRequest, AdminUserUpdateRequest,
    SupportStaffCreateRequest, SystemStats,
    StandardResponse, PaginatedResponse
)
from app.services.admin_service import admin_service
from app.services.support_service import support_service
from app.security.firewall import firewall
from app.security.encryption import security_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Management"])
security = HTTPBearer()


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated admin from JWT token"""
    try:
        # Verify JWT token
        payload = security_manager.verify_jwt_token(credentials.credentials)
        if not payload or payload.get('user_type') != 'admin':
            raise HTTPException(status_code=401, detail="Admin authentication required")
        
        # Validate session
        session = admin_service.db.validate_session(payload.get('session_id', ''))
        if not session:
            raise HTTPException(status_code=401, detail="Admin session expired")
        
        return payload
        
    except Exception as e:
        logger.error(f"Admin authentication error: {e}")
        raise HTTPException(status_code=401, detail="Admin authentication failed")


@router.post("/login")
async def admin_login(request: AdminLoginRequest, http_request: Request):
    """Admin login"""
    client_ip = get_client_ip(http_request)
    
    # Check firewall
    allowed, reason = firewall.is_ip_allowed(client_ip)
    if not allowed:
        firewall.record_security_event(
            client_ip, "blocked_admin_login", "critical",
            f"Admin login blocked: {reason}"
        )
        raise HTTPException(status_code=403, detail=f"Access denied: {reason}")
    
    try:
        success, message, data = await admin_service.admin_login(request, client_ip)
        
        if success:
            return {
                "success": True,
                "message": message,
                "access_token": data['access_token'],
                "session_id": data['session_id'],
                "admin_info": data['admin_info']
            }
        else:
            # Record failed admin login attempt
            firewall.record_security_event(
                client_ip, "failed_admin_login", "high",
                f"Failed admin login attempt: {message}"
            )
            raise HTTPException(status_code=401, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Get system statistics"""
    try:
        stats = await admin_service.get_system_stats()
        return SystemStats(**stats)
        
    except Exception as e:
        logger.error(f"Get system stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users")
async def get_all_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get all users with pagination"""
    try:
        users, total = await admin_service.get_all_users(limit, offset)
        
        return PaginatedResponse(
            success=True,
            data=users,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(users) < total
        )
        
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{username}")
async def get_user_details(
    username: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get detailed user information"""
    try:
        user = await admin_service.get_user_details(username)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "data": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user details error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{username}", response_model=StandardResponse)
async def update_user(
    username: str,
    request: AdminUserUpdateRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Update user information"""
    try:
        success, message = await admin_service.update_user(username, request)
        
        if success:
            # Log admin action
            firewall.record_security_event(
                "", "admin_user_update", "medium",
                f"Admin {current_admin['username']} updated user {username}"
            )
            return StandardResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/users/{username}", response_model=StandardResponse)
async def delete_user(
    username: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Delete user account"""
    try:
        success, message = await admin_service.delete_user(username, current_admin['username'])
        
        if success:
            # Log admin action
            firewall.record_security_event(
                "", "admin_user_delete", "high",
                f"Admin {current_admin['username']} deleted user {username}"
            )
            return StandardResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{username}/messages")
async def get_user_messages(
    username: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get user message logs"""
    try:
        logs, total = await admin_service.get_user_message_logs(username, limit, offset)
        
        return PaginatedResponse(
            success=True,
            data=logs,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(logs) < total
        )
        
    except Exception as e:
        logger.error(f"Get user messages error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Support Staff Management
@router.post("/support-staff", response_model=StandardResponse)
async def create_support_staff(
    request: SupportStaffCreateRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Create support staff member"""
    try:
        success, message, staff_id = await admin_service.create_support_staff(request, current_admin['username'])
        
        if success:
            # Log admin action
            firewall.record_security_event(
                "", "admin_staff_create", "medium",
                f"Admin {current_admin['username']} created support staff {request.username}"
            )
            return StandardResponse(
                success=True,
                message=message,
                data={"staff_id": staff_id}
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create support staff error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/support-staff")
async def get_all_support_staff(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Get all support staff"""
    try:
        staff_list = await admin_service.get_all_support_staff()
        
        return {
            "success": True,
            "data": staff_list
        }
        
    except Exception as e:
        logger.error(f"Get support staff error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/support-staff/{staff_id}/status", response_model=StandardResponse)
async def update_support_staff_status(
    staff_id: str,
    is_active: bool,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Update support staff active status"""
    try:
        success, message = await admin_service.update_support_staff_status(staff_id, is_active)
        
        if success:
            # Log admin action
            action = "activated" if is_active else "deactivated"
            firewall.record_security_event(
                "", "admin_staff_status_update", "medium",
                f"Admin {current_admin['username']} {action} support staff {staff_id}"
            )
            return StandardResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update support staff status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Security Management
@router.get("/security/events")
async def get_security_events(
    hours: int = Query(24, ge=1, le=168),  # Last 24 hours by default, max 7 days
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get recent security events"""
    try:
        events = firewall.get_security_events(hours)
        
        # Convert to serializable format
        events_data = []
        for event in events:
            events_data.append({
                "timestamp": event.timestamp.isoformat(),
                "ip_address": event.ip_address,
                "event_type": event.event_type,
                "severity": event.severity,
                "description": event.description,
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "blocked": event.blocked
            })
        
        return {
            "success": True,
            "data": events_data,
            "total": len(events_data)
        }
        
    except Exception as e:
        logger.error(f"Get security events error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/firewall/stats")
async def get_firewall_stats(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Get firewall statistics"""
    try:
        stats = firewall.get_stats()
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Get firewall stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/firewall/block-ip", response_model=StandardResponse)
async def block_ip(
    ip_address: str,
    reason: str,
    hours: int = 24,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Block IP address"""
    try:
        success = firewall.block_ip(ip_address, reason, current_admin['username'], hours)
        
        if success:
            firewall.record_security_event(
                "", "admin_ip_block", "medium",
                f"Admin {current_admin['username']} blocked IP {ip_address}: {reason}"
            )
            return StandardResponse(
                success=True,
                message=f"IP {ip_address} blocked successfully"
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to block IP")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Block IP error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/firewall/whitelist-ip", response_model=StandardResponse)
async def whitelist_ip(
    ip_address: str,
    reason: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Whitelist IP address"""
    try:
        success = firewall.whitelist_ip(ip_address, reason, current_admin['username'])
        
        if success:
            firewall.record_security_event(
                "", "admin_ip_whitelist", "low",
                f"Admin {current_admin['username']} whitelisted IP {ip_address}: {reason}"
            )
            return StandardResponse(
                success=True,
                message=f"IP {ip_address} whitelisted successfully"
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to whitelist IP")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Whitelist IP error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/firewall/enable-whitelist", response_model=StandardResponse)
async def enable_whitelist_mode(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Enable whitelist mode"""
    try:
        firewall.enable_whitelist_mode()
        
        firewall.record_security_event(
            "", "admin_whitelist_enable", "high",
            f"Admin {current_admin['username']} enabled whitelist mode"
        )
        
        return StandardResponse(
            success=True,
            message="Whitelist mode enabled"
        )
        
    except Exception as e:
        logger.error(f"Enable whitelist mode error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/firewall/disable-whitelist", response_model=StandardResponse)
async def disable_whitelist_mode(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Disable whitelist mode"""
    try:
        firewall.disable_whitelist_mode()
        
        firewall.record_security_event(
            "", "admin_whitelist_disable", "medium",
            f"Admin {current_admin['username']} disabled whitelist mode"
        )
        
        return StandardResponse(
            success=True,
            message="Whitelist mode disabled"
        )
        
    except Exception as e:
        logger.error(f"Disable whitelist mode error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout", response_model=StandardResponse)
async def admin_logout(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """Admin logout"""
    try:
        # Invalidate session
        with admin_service.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
                (current_admin.get('session_id', ''),)
            )
        
        return StandardResponse(
            success=True,
            message="Admin logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")