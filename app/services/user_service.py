"""
User management service for registration, authentication, and profile management
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from email_validator import validate_email, EmailNotValidError

from app.database.models import User, UserSession, DeletedUser, SecurityLog
from app.security.encryption import (
    password_manager, 
    token_manager, 
    encryption_manager
)
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class UserService:
    """Service for user management operations"""
    
    def __init__(self):
        self.session_duration_hours = 24
        self.refresh_token_duration_days = 30
        
    async def register_user(
        self, 
        session: AsyncSession,
        username: str,
        name: str,
        email: str,
        password: str,
        user_type: str = "Personal",
        about_me: str = "",
        hobbies: str = "",
        ip_address: str = None
    ) -> Dict[str, Any]:
        """Register a new user"""
        
        # Validate input data
        validation_errors = await self._validate_registration_data(
            session, username, name, email, password
        )
        
        if validation_errors:
            await self._log_security_event(
                session, "registration_failed", 
                ip_address=ip_address,
                details={"errors": validation_errors, "username": username, "email": email}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Registration failed", "errors": validation_errors}
            )
        
        try:
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Generate unique API key
            api_key = await self._generate_unique_api_key(session)
            
            # Create user record
            user = User(
                username=username,
                name=name,
                email=email.lower(),
                password_hash=password_hash,
                about_me=about_me,
                hobbies=hobbies,
                user_type=user_type,
                api_key=api_key,
                is_active=True,
                is_verified=False  # Email verification required
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            await self._log_security_event(
                session, "user_registered",
                user_id=user.id,
                username=username,
                ip_address=ip_address,
                details={"user_type": user_type}
            )
            
            logger.info(f"User registered successfully: {username}")
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "api_key": user.api_key,
                "verification_required": True
            }
            
        except IntegrityError as e:
            await session.rollback()
            
            if "username" in str(e):
                error_msg = "Username already exists"
            elif "email" in str(e):
                error_msg = "Email already exists"
            else:
                error_msg = "User already exists"
            
            await self._log_security_event(
                session, "registration_failed",
                ip_address=ip_address,
                details={"error": error_msg, "username": username, "email": email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": error_msg}
            )
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Registration failed for {username}: {e}")
            
            await self._log_security_event(
                session, "registration_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Registration failed due to server error"}
            )
    
    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate user and create session"""
        
        try:
            # Find user by email
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await self._log_security_event(
                    session, "login_failed",
                    ip_address=ip_address,
                    details={"reason": "user_not_found", "email": email}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if user is active
            if not user.is_active:
                await self._log_security_event(
                    session, "login_failed",
                    user_id=user.id,
                    username=user.username,
                    ip_address=ip_address,
                    details={"reason": "account_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Account is inactive"}
                )
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now():
                await self._log_security_event(
                    session, "login_failed",
                    user_id=user.id,
                    username=user.username,
                    ip_address=ip_address,
                    details={"reason": "account_locked", "locked_until": user.locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Account locked until {user.locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now() + timedelta(hours=1)
                
                await session.commit()
                
                await self._log_security_event(
                    session, "login_failed",
                    user_id=user.id,
                    username=user.username,
                    ip_address=ip_address,
                    details={
                        "reason": "invalid_password",
                        "failed_attempts": user.failed_login_attempts
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_login = datetime.now()
            user.last_activity = datetime.now()
            
            # Create session
            session_token = token_manager.generate_session_token()
            refresh_token = token_manager.generate_session_token()
            
            expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            refresh_expires_at = datetime.now() + timedelta(days=self.refresh_token_duration_days)
            
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session.add(user_session)
            await session.commit()
            
            await self._log_security_event(
                session, "login_successful",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"session_id": user_session.id}
            )
            
            logger.info(f"User logged in successfully: {user.username}")
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "email": user.email,
                    "user_type": user.user_type,
                    "subscription_plan": user.subscription_plan,
                    "is_verified": user.is_verified
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
            logger.error(f"Authentication failed for {email}: {e}")
            
            await self._log_security_event(
                session, "login_error",
                ip_address=ip_address,
                details={"error": str(e), "email": email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Authentication failed due to server error"}
            )
    
    async def validate_session(
        self,
        session: AsyncSession,
        session_token: str
    ) -> Optional[User]:
        """Validate session token and return user"""
        
        try:
            result = await session.execute(
                select(UserSession).where(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now()
                )
            )
            user_session = result.scalar_one_or_none()
            
            if not user_session:
                return None
            
            # Get user
            result = await session.execute(
                select(User).where(User.id == user_session.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                return None
            
            # Update session last used
            user_session.last_used = datetime.now()
            user.last_activity = datetime.now()
            await session.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    async def validate_api_key(
        self,
        session: AsyncSession,
        api_key: str
    ) -> Optional[User]:
        """Validate API key and return user"""
        
        try:
            result = await session.execute(
                select(User).where(
                    User.api_key == api_key,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update last activity
                user.last_activity = datetime.now()
                await session.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return None
    
    async def refresh_session(
        self,
        session: AsyncSession,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Refresh session using refresh token"""
        
        try:
            result = await session.execute(
                select(UserSession).where(
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True,
                    UserSession.refresh_expires_at > datetime.now()
                )
            )
            user_session = result.scalar_one_or_none()
            
            if not user_session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid refresh token"}
                )
            
            # Generate new tokens
            new_session_token = token_manager.generate_session_token()
            new_refresh_token = token_manager.generate_session_token()
            
            # Update session
            user_session.session_token = new_session_token
            user_session.refresh_token = new_refresh_token
            user_session.expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            user_session.refresh_expires_at = datetime.now() + timedelta(days=self.refresh_token_duration_days)
            user_session.last_used = datetime.now()
            
            await session.commit()
            
            return {
                "success": True,
                "session": {
                    "session_token": new_session_token,
                    "refresh_token": new_refresh_token,
                    "expires_at": user_session.expires_at.isoformat(),
                    "refresh_expires_at": user_session.refresh_expires_at.isoformat()
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Session refresh failed"}
            )
    
    async def logout_user(
        self,
        session: AsyncSession,
        session_token: str
    ) -> Dict[str, Any]:
        """Logout user by invalidating session"""
        
        try:
            result = await session.execute(
                select(UserSession).where(UserSession.session_token == session_token)
            )
            user_session = result.scalar_one_or_none()
            
            if user_session:
                user_session.is_active = False
                await session.commit()
            
            return {"success": True, "message": "Logged out successfully"}
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Logout failed"}
            )
    
    async def regenerate_api_key(
        self,
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Regenerate API key for user"""
        
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
            
            # Generate new API key
            old_api_key = user.api_key
            new_api_key = await self._generate_unique_api_key(session)
            
            user.api_key = new_api_key
            await session.commit()
            
            await self._log_security_event(
                session, "api_key_regenerated",
                user_id=user.id,
                username=user.username,
                details={"old_key_prefix": old_api_key[:10], "new_key_prefix": new_api_key[:10]}
            )
            
            return {
                "success": True,
                "message": "API key regenerated successfully",
                "api_key": encryption_manager.encrypt(new_api_key)  # Return encrypted
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key regeneration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "API key regeneration failed"}
            )
    
    async def _validate_registration_data(
        self,
        session: AsyncSession,
        username: str,
        name: str,
        email: str,
        password: str
    ) -> List[str]:
        """Validate registration data"""
        errors = []
        
        # Validate username
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        elif len(username) > 50:
            errors.append("Username must be less than 50 characters")
        elif not username.replace('_', '').replace('-', '').isalnum():
            errors.append("Username can only contain letters, numbers, hyphens, and underscores")
        
        # Check if username exists
        if username:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                errors.append("Username already exists")
        
        # Validate name
        if not name or len(name) < 2:
            errors.append("Name must be at least 2 characters long")
        elif len(name) > 100:
            errors.append("Name must be less than 100 characters")
        
        # Validate email
        try:
            validated_email = validate_email(email)
            email = validated_email.email
        except EmailNotValidError:
            errors.append("Invalid email format")
        
        # Check if email exists
        if email:
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            if result.scalar_one_or_none():
                errors.append("Email already exists")
        
        # Validate password
        is_strong, password_errors = password_manager.validate_password_strength(password)
        if not is_strong:
            errors.extend(password_errors)
        
        return errors
    
    async def _generate_unique_api_key(self, session: AsyncSession) -> str:
        """Generate unique API key"""
        max_attempts = 10
        
        for _ in range(max_attempts):
            api_key = token_manager.generate_api_key()
            
            # Check if key already exists
            result = await session.execute(
                select(User).where(User.api_key == api_key)
            )
            
            if not result.scalar_one_or_none():
                return api_key
        
        raise Exception("Failed to generate unique API key")
    
    async def _log_security_event(
        self,
        session: AsyncSession,
        event_type: str,
        user_id: int = None,
        username: str = None,
        ip_address: str = None,
        details: dict = None,
        severity: str = "info"
    ):
        """Log security event"""
        try:
            # Use a separate session for security logging to avoid transaction conflicts
            from app.database.database import get_db_session_context
            async with get_db_session_context() as log_session:
                security_log = SecurityLog(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address,
                    details=details,
                    severity=severity
                )
                log_session.add(security_log)
                await log_session.commit()
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


# Global service instance
user_service = UserService()