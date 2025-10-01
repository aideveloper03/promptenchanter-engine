"""
Admin management service for user administration and system control
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.database.models import (
    Admin, User, UserSession, MessageLog, SecurityLog, 
    IPWhitelist, APIUsageLog, DeletedUser, SupportStaff
)
from app.security.encryption import (
    password_manager, 
    token_manager, 
    encryption_manager
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdminService:
    """Service for admin management operations"""
    
    def __init__(self):
        self.session_duration_hours = 24
        self.refresh_token_duration_days = 7  # Shorter for admin sessions
    
    async def create_admin(
        self,
        session: AsyncSession,
        username: str,
        name: str,
        email: str,
        password: str,
        is_super_admin: bool = False,
        permissions: List[str] = None,
        created_by: str = None
    ) -> Dict[str, Any]:
        """Create a new admin user"""
        
        try:
            # Validate password strength
            is_strong, errors = password_manager.validate_password_strength(password)
            if not is_strong:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Password does not meet requirements", "errors": errors}
                )
            
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Create admin record
            admin = Admin(
                username=username,
                name=name,
                email=email.lower(),
                password_hash=password_hash,
                is_super_admin=is_super_admin,
                permissions=permissions or [],
                created_by=created_by
            )
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            logger.info(f"Admin created: {username} by {created_by}")
            
            return {
                "success": True,
                "message": "Admin created successfully",
                "admin_id": admin.id,
                "username": admin.username
            }
            
        except IntegrityError as e:
            await session.rollback()
            
            if "username" in str(e):
                error_msg = "Username already exists"
            elif "email" in str(e):
                error_msg = "Email already exists"
            else:
                error_msg = "Admin already exists"
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": error_msg}
            )
        
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Admin creation failed for {username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Admin creation failed"}
            )
    
    async def authenticate_admin(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate admin and create session"""
        
        try:
            # Find admin by username
            result = await session.execute(
                select(Admin).where(Admin.username == username)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                await self._log_admin_security_event(
                    session, "admin_login_failed",
                    ip_address=ip_address,
                    details={"reason": "admin_not_found", "username": username}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if admin is active
            if not admin.is_active:
                await self._log_admin_security_event(
                    session, "admin_login_failed",
                    username=admin.username,
                    ip_address=ip_address,
                    details={"reason": "admin_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Admin account is inactive"}
                )
            
            # Check if account is locked
            if admin.locked_until and admin.locked_until > datetime.now():
                await self._log_admin_security_event(
                    session, "admin_login_failed",
                    username=admin.username,
                    ip_address=ip_address,
                    details={"reason": "admin_locked", "locked_until": admin.locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Admin account locked until {admin.locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, admin.password_hash):
                # Increment failed attempts
                admin.failed_login_attempts += 1
                
                # Lock account after 3 failed attempts (stricter for admins)
                if admin.failed_login_attempts >= 3:
                    admin.locked_until = datetime.now() + timedelta(hours=2)
                
                await session.commit()
                
                await self._log_admin_security_event(
                    session, "admin_login_failed",
                    username=admin.username,
                    ip_address=ip_address,
                    details={
                        "reason": "invalid_password",
                        "failed_attempts": admin.failed_login_attempts
                    },
                    severity="warning"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if password hash needs upgrade (bcrypt -> argon2id)
            if password_manager.needs_rehash(admin.password_hash):
                # Upgrade the hash to argon2id
                new_hash = password_manager.hash_password(password)
                admin.password_hash = new_hash
                
                await self._log_admin_security_event(
                    session, "admin_password_hash_upgraded",
                    username=admin.username,
                    ip_address=ip_address,
                    details={"from": "bcrypt", "to": "argon2id"}
                )
            
            # Reset failed attempts on successful login
            admin.failed_login_attempts = 0
            admin.last_login = datetime.now()
            
            # Create session token (using same UserSession table with negative user_id for admins)
            session_token = token_manager.generate_session_token()
            refresh_token = token_manager.generate_session_token()
            
            expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            refresh_expires_at = datetime.now() + timedelta(days=self.refresh_token_duration_days)
            
            admin_session = UserSession(
                user_id=-admin.id,  # Negative ID to distinguish from regular users
                session_token=session_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session.add(admin_session)
            await session.commit()
            
            await self._log_admin_security_event(
                session, "admin_login_successful",
                username=admin.username,
                ip_address=ip_address,
                details={"session_id": admin_session.id}
            )
            
            logger.info(f"Admin logged in successfully: {admin.username}")
            
            return {
                "success": True,
                "message": "Admin login successful",
                "admin": {
                    "id": admin.id,
                    "username": admin.username,
                    "name": admin.name,
                    "email": admin.email,
                    "is_super_admin": admin.is_super_admin,
                    "permissions": admin.permissions
                },
                "session": {
                    "session_token": session_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at.isoformat(),
                    "refresh_expires_at": refresh_expires_at.isoformat()
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin authentication failed for {username}: {e}")
            
            await self._log_admin_security_event(
                session, "admin_login_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username},
                severity="error"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Admin authentication failed"}
            )
    
    async def validate_admin_session(
        self,
        session: AsyncSession,
        session_token: str
    ) -> Optional[Admin]:
        """Validate admin session token and return admin"""
        
        try:
            result = await session.execute(
                select(UserSession).where(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(),
                    UserSession.user_id < 0  # Admin sessions have negative user_id
                )
            )
            admin_session = result.scalar_one_or_none()
            
            if not admin_session:
                return None
            
            # Get admin (convert negative user_id back to positive admin_id)
            admin_id = -admin_session.user_id
            result = await session.execute(
                select(Admin).where(Admin.id == admin_id)
            )
            admin = result.scalar_one_or_none()
            
            if not admin or not admin.is_active:
                return None
            
            # Update session last used
            admin_session.last_used = datetime.now()
            await session.commit()
            
            return admin
            
        except Exception as e:
            logger.error(f"Admin session validation failed: {e}")
            return None
    
    async def get_users_list(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        search: str = None,
        user_type: str = None,
        is_active: bool = None,
        is_verified: bool = None
    ) -> Dict[str, Any]:
        """Get paginated list of users with filtering"""
        
        try:
            # Build query
            query = select(User)
            
            # Apply filters
            if search:
                search_filter = or_(
                    User.username.ilike(f"%{search}%"),
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
                query = query.where(search_filter)
            
            if user_type:
                query = query.where(User.user_type == user_type)
            
            if is_active is not None:
                query = query.where(User.is_active == is_active)
            
            if is_verified is not None:
                query = query.where(User.is_verified == is_verified)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(User.time_created.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await session.execute(query)
            users = result.scalars().all()
            
            return {
                "users": users,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get users list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to retrieve users"}
            )
    
    async def update_user(
        self,
        session: AsyncSession,
        user_id: int,
        updates: Dict[str, Any],
        admin_username: str
    ) -> Dict[str, Any]:
        """Update user information"""
        
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
            
            # Apply updates
            original_values = {}
            for field, value in updates.items():
                if hasattr(user, field) and value is not None:
                    original_values[field] = getattr(user, field)
                    setattr(user, field, value)
            
            await session.commit()
            
            # Log the update
            await self._log_admin_security_event(
                session, "user_updated",
                username=admin_username,
                details={
                    "target_user_id": user_id,
                    "target_username": user.username,
                    "updates": updates,
                    "original_values": original_values
                }
            )
            
            logger.info(f"User {user.username} updated by admin {admin_username}")
            
            return {
                "success": True,
                "message": "User updated successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to update user"}
            )
    
    async def delete_user(
        self,
        session: AsyncSession,
        user_id: int,
        admin_username: str,
        reason: str = "Admin deletion"
    ) -> Dict[str, Any]:
        """Delete user account (admin action)"""
        
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
            
            # Archive user data
            deleted_user = DeletedUser(
                original_user_id=user.id,
                username=user.username,
                name=user.name,
                email=user.email,
                user_type=user.user_type,
                time_created=user.time_created,
                subscription_plan=user.subscription_plan,
                deletion_reason=reason,
                deleted_by=admin_username
            )
            
            session.add(deleted_user)
            
            # Delete user (cascades to sessions and messages)
            await session.delete(user)
            await session.commit()
            
            # Log the deletion
            await self._log_admin_security_event(
                session, "user_deleted",
                username=admin_username,
                details={
                    "target_user_id": user_id,
                    "target_username": user.username,
                    "reason": reason
                },
                severity="warning"
            )
            
            logger.warning(f"User {user.username} deleted by admin {admin_username}")
            
            return {
                "success": True,
                "message": "User deleted successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to delete user"}
            )
    
    async def get_system_statistics(
        self,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        
        try:
            # User statistics
            total_users_result = await session.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar()
            
            active_users_result = await session.execute(
                select(func.count(User.id)).where(User.is_active == True)
            )
            active_users = active_users_result.scalar()
            
            verified_users_result = await session.execute(
                select(func.count(User.id)).where(User.is_verified == True)
            )
            verified_users = verified_users_result.scalar()
            
            # New users today
            today = datetime.now().date()
            new_users_today_result = await session.execute(
                select(func.count(User.id)).where(
                    func.date(User.time_created) == today
                )
            )
            new_users_today = new_users_today_result.scalar()
            
            # API usage statistics
            total_api_calls_result = await session.execute(select(func.count(APIUsageLog.id)))
            total_api_calls = total_api_calls_result.scalar()
            
            api_calls_today_result = await session.execute(
                select(func.count(APIUsageLog.id)).where(
                    APIUsageLog.date == today.strftime("%Y-%m-%d")
                )
            )
            api_calls_today = api_calls_today_result.scalar()
            
            # Message statistics
            total_messages_result = await session.execute(select(func.count(MessageLog.id)))
            total_messages = total_messages_result.scalar()
            
            total_tokens_result = await session.execute(select(func.sum(MessageLog.tokens_used)))
            total_tokens = total_tokens_result.scalar() or 0
            
            # Active sessions
            active_sessions_result = await session.execute(
                select(func.count(UserSession.id)).where(
                    and_(
                        UserSession.is_active == True,
                        UserSession.expires_at > datetime.now()
                    )
                )
            )
            active_sessions = active_sessions_result.scalar()
            
            return {
                "user_statistics": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "verified_users": verified_users,
                    "new_users_today": new_users_today
                },
                "api_statistics": {
                    "total_api_calls": total_api_calls,
                    "api_calls_today": api_calls_today,
                    "total_messages": total_messages,
                    "total_tokens_used": total_tokens
                },
                "system_statistics": {
                    "active_sessions": active_sessions,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to retrieve system statistics"}
            )
    
    async def _log_admin_security_event(
        self,
        session: AsyncSession,
        event_type: str,
        username: str = None,
        ip_address: str = None,
        details: dict = None,
        severity: str = "info"
    ):
        """Log admin security event"""
        try:
            # Use a separate session for security logging to avoid transaction conflicts
            from app.database.database import get_db_session_context
            async with get_db_session_context() as log_session:
                security_log = SecurityLog(
                    event_type=event_type,
                    username=username,
                    ip_address=ip_address,
                    details=details,
                    severity=severity
                )
                log_session.add(security_log)
                await log_session.commit()
        except Exception as e:
            logger.error(f"Failed to log admin security event: {e}")


# Global service instance
admin_service = AdminService()