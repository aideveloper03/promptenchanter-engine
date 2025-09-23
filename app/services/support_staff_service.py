"""
Support staff management service
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.database.models import SupportStaff, User, UserSession, SecurityLog
from app.security.encryption import password_manager, token_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupportStaffService:
    """Service for support staff management operations"""
    
    def __init__(self):
        self.session_duration_hours = 12  # Shorter sessions for support staff
        self.refresh_token_duration_days = 3
        
        # Define permissions for each staff level
        self.staff_permissions = {
            "new": {
                "can_view_users": True,
                "can_view_passwords": False,
                "can_update_users": False,
                "can_delete_users": False,
                "can_view_messages": False,
                "can_update_credits": False,
                "can_update_plans": False
            },
            "support": {
                "can_view_users": True,
                "can_view_passwords": False,
                "can_update_users": True,
                "can_delete_users": False,
                "can_view_messages": False,
                "can_update_credits": True,
                "can_update_plans": True,
                "can_reset_passwords": True,
                "can_update_emails": True
            },
            "advanced": {
                "can_view_users": True,
                "can_view_passwords": False,
                "can_update_users": True,
                "can_delete_users": False,  # Still cannot delete unless specified
                "can_view_messages": True,
                "can_update_credits": True,
                "can_update_plans": True,
                "can_reset_passwords": True,
                "can_update_emails": True,
                "can_manage_api_keys": True,
                "can_view_security_logs": True
            }
        }
    
    async def create_support_staff(
        self,
        session: AsyncSession,
        username: str,
        name: str,
        email: str,
        password: str,
        staff_level: str = "new",
        created_by: str = None
    ) -> Dict[str, Any]:
        """Create a new support staff member"""
        
        try:
            # Validate staff level
            if staff_level not in self.staff_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": f"Invalid staff level: {staff_level}"}
                )
            
            # Validate password strength
            is_strong, errors = password_manager.validate_password_strength(password)
            if not is_strong:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Password does not meet requirements", "errors": errors}
                )
            
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Create staff record
            staff = SupportStaff(
                username=username,
                name=name,
                email=email.lower(),
                password_hash=password_hash,
                staff_level=staff_level,
                created_by=created_by or "system"
            )
            
            session.add(staff)
            await session.commit()
            await session.refresh(staff)
            
            logger.info(f"Support staff created: {username} (level: {staff_level}) by {created_by}")
            
            return {
                "success": True,
                "message": "Support staff created successfully",
                "staff_id": staff.id,
                "username": staff.username,
                "staff_level": staff.staff_level
            }
            
        except IntegrityError as e:
            await session.rollback()
            
            if "username" in str(e):
                error_msg = "Username already exists"
            elif "email" in str(e):
                error_msg = "Email already exists"
            else:
                error_msg = "Staff member already exists"
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": error_msg}
            )
        
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Support staff creation failed for {username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Support staff creation failed"}
            )
    
    async def authenticate_support_staff(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate support staff and create session"""
        
        try:
            # Find staff by username
            result = await session.execute(
                select(SupportStaff).where(SupportStaff.username == username)
            )
            staff = result.scalar_one_or_none()
            
            if not staff:
                await self._log_security_event(
                    session, "support_login_failed",
                    ip_address=ip_address,
                    details={"reason": "staff_not_found", "username": username}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if staff is active
            if not staff.is_active:
                await self._log_security_event(
                    session, "support_login_failed",
                    username=staff.username,
                    ip_address=ip_address,
                    details={"reason": "staff_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Support staff account is inactive"}
                )
            
            # Check if account is locked
            if staff.locked_until and staff.locked_until > datetime.now():
                await self._log_security_event(
                    session, "support_login_failed",
                    username=staff.username,
                    ip_address=ip_address,
                    details={"reason": "staff_locked", "locked_until": staff.locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Support staff account locked until {staff.locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, staff.password_hash):
                # Increment failed attempts
                staff.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if staff.failed_login_attempts >= 5:
                    staff.locked_until = datetime.now() + timedelta(hours=1)
                
                await session.commit()
                
                await self._log_security_event(
                    session, "support_login_failed",
                    username=staff.username,
                    ip_address=ip_address,
                    details={
                        "reason": "invalid_password",
                        "failed_attempts": staff.failed_login_attempts
                    },
                    severity="warning"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Reset failed attempts on successful login
            staff.failed_login_attempts = 0
            staff.last_login = datetime.now()
            
            # Create session token (using UserSession table with negative user_id for support staff)
            session_token = token_manager.generate_session_token()
            refresh_token = token_manager.generate_session_token()
            
            expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            refresh_expires_at = datetime.now() + timedelta(days=self.refresh_token_duration_days)
            
            # Use negative ID with offset to distinguish from admins (-1000 - staff_id)
            staff_session = UserSession(
                user_id=(-1000 - staff.id),
                session_token=session_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session.add(staff_session)
            await session.commit()
            
            await self._log_security_event(
                session, "support_login_successful",
                username=staff.username,
                ip_address=ip_address,
                details={"session_id": staff_session.id, "staff_level": staff.staff_level}
            )
            
            logger.info(f"Support staff logged in successfully: {staff.username}")
            
            return {
                "success": True,
                "message": "Support staff login successful",
                "staff": {
                    "id": staff.id,
                    "username": staff.username,
                    "name": staff.name,
                    "email": staff.email,
                    "staff_level": staff.staff_level,
                    "is_active": staff.is_active,
                    "time_created": staff.time_created,
                    "created_by": staff.created_by,
                    "last_login": staff.last_login
                },
                "session": {
                    "session_token": session_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at.isoformat(),
                    "refresh_expires_at": refresh_expires_at.isoformat()
                },
                "permissions": self.staff_permissions.get(staff.staff_level, {})
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Support staff authentication failed for {username}: {e}")
            
            await self._log_security_event(
                session, "support_login_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username},
                severity="error"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Support staff authentication failed"}
            )
    
    async def validate_support_staff_session(
        self,
        session: AsyncSession,
        session_token: str
    ) -> Optional[SupportStaff]:
        """Validate support staff session token and return staff"""
        
        try:
            result = await session.execute(
                select(UserSession).where(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(),
                    UserSession.user_id <= -1000  # Support staff sessions
                )
            )
            staff_session = result.scalar_one_or_none()
            
            if not staff_session:
                return None
            
            # Get staff (convert negative user_id back to positive staff_id)
            staff_id = -staff_session.user_id - 1000
            result = await session.execute(
                select(SupportStaff).where(SupportStaff.id == staff_id)
            )
            staff = result.scalar_one_or_none()
            
            if not staff or not staff.is_active:
                return None
            
            # Update session last used
            staff_session.last_used = datetime.now()
            await session.commit()
            
            return staff
            
        except Exception as e:
            logger.error(f"Support staff session validation failed: {e}")
            return None
    
    def check_permission(self, staff: SupportStaff, permission: str) -> bool:
        """Check if support staff has a specific permission"""
        staff_perms = self.staff_permissions.get(staff.staff_level, {})
        return staff_perms.get(permission, False)
    
    async def update_user_limited(
        self,
        session: AsyncSession,
        staff: SupportStaff,
        user_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user with support staff permissions"""
        
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "User not found"}
                )
            
            # Filter updates based on staff level permissions
            allowed_updates = {}
            
            if staff.staff_level == "new":
                # New staff can't update anything
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"message": "Insufficient permissions to update users"}
                )
            
            elif staff.staff_level == "support":
                # Support staff can update specific fields
                allowed_fields = ["email", "limits", "subscription_plan"]
                if "password" in updates and self.check_permission(staff, "can_reset_passwords"):
                    # Handle password reset
                    new_password = updates["password"]
                    is_strong, errors = password_manager.validate_password_strength(new_password)
                    if not is_strong:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": "Password does not meet requirements", "errors": errors}
                        )
                    allowed_updates["password_hash"] = password_manager.hash_password(new_password)
                
                for field, value in updates.items():
                    if field in allowed_fields and value is not None:
                        allowed_updates[field] = value
            
            elif staff.staff_level == "advanced":
                # Advanced staff can update most fields
                restricted_fields = ["id", "username", "api_key", "time_created"]
                
                if "password" in updates:
                    # Handle password reset
                    new_password = updates["password"]
                    is_strong, errors = password_manager.validate_password_strength(new_password)
                    if not is_strong:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": "Password does not meet requirements", "errors": errors}
                        )
                    allowed_updates["password_hash"] = password_manager.hash_password(new_password)
                
                for field, value in updates.items():
                    if field not in restricted_fields and field != "password" and value is not None:
                        allowed_updates[field] = value
            
            if not allowed_updates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "No valid updates provided"}
                )
            
            # Apply updates
            original_values = {}
            for field, value in allowed_updates.items():
                if hasattr(user, field):
                    original_values[field] = getattr(user, field)
                    setattr(user, field, value)
            
            await session.commit()
            
            # Log the update
            await self._log_security_event(
                session, "user_updated_by_support",
                username=staff.username,
                details={
                    "target_user_id": user_id,
                    "target_username": user.username,
                    "staff_level": staff.staff_level,
                    "updates": {k: v for k, v in allowed_updates.items() if k != "password_hash"},
                    "original_values": {k: v for k, v in original_values.items() if k != "password_hash"}
                }
            )
            
            logger.info(f"User {user.username} updated by support staff {staff.username}")
            
            return {
                "success": True,
                "message": "User updated successfully",
                "updated_fields": list(allowed_updates.keys())
            }
            
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update user {user_id} by support staff {staff.username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to update user"}
            )
    
    async def _log_security_event(
        self,
        session: AsyncSession,
        event_type: str,
        username: str = None,
        ip_address: str = None,
        details: dict = None,
        severity: str = "info"
    ):
        """Log security event"""
        try:
            security_log = SecurityLog(
                event_type=event_type,
                username=username,
                ip_address=ip_address,
                details=details,
                severity=severity
            )
            session.add(security_log)
            await session.flush()
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


# Global service instance
support_staff_service = SupportStaffService()