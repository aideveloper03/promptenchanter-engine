"""
MongoDB-based user management service for PromptEnchanter
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status
from email_validator import validate_email, EmailNotValidError

from app.database.mongodb import get_mongodb_collection, MongoDBUtils
from app.security.encryption import (
    password_manager, 
    token_manager, 
    encryption_manager
)
from app.services.email_service import email_service
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MongoDBUserService:
    """MongoDB-based service for user management operations"""
    
    def __init__(self):
        self.session_duration_hours = settings.session_duration_hours
        self.refresh_token_duration_days = settings.refresh_token_duration_days
        
    async def register_user(
        self, 
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
            username, name, email, password
        )
        
        if validation_errors:
            await self._log_security_event(
                "registration_failed", 
                ip_address=ip_address,
                details={"errors": validation_errors, "username": username, "email": email}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Registration failed", "errors": validation_errors}
            )
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Generate unique API key
            api_key = await self._generate_unique_api_key()
            
            # Generate user ID
            user_id = MongoDBUtils.generate_object_id()
            
            # Create user document
            user_doc = {
                "_id": user_id,
                "username": username,
                "name": name,
                "email": email.lower(),
                "password_hash": password_hash,
                "about_me": about_me,
                "hobbies": hobbies,
                "user_type": user_type,
                "time_created": datetime.now(),
                "subscription_plan": "free",
                "credits": settings.default_user_credits,
                "limits": settings.default_user_limits,
                "access_rtype": settings.default_user_access_rtype,
                "level": settings.default_user_level,
                "additional_notes": "",
                "api_key": api_key,
                "is_active": True,
                "is_verified": not settings.email_verification_enabled,  # Auto-verify if disabled
                "email_verification_token": None,
                "password_reset_token": None,
                "password_reset_expires": None,
                "last_login": None,
                "failed_login_attempts": 0,
                "locked_until": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_activity": datetime.now()
            }
            
            # Insert user
            await users_collection.insert_one(user_doc)
            
            # Send verification email if enabled
            verification_required = False
            if settings.email_verification_enabled:
                try:
                    verification_result = await email_service.send_verification_email(
                        str(user_id), email.lower(), name
                    )
                    verification_required = verification_result.get("success", False)
                    logger.info(f"Email verification result for {username}: {verification_result.get('message', 'Unknown')}")
                except Exception as email_error:
                    logger.error(f"Email verification failed for {username}: {email_error}")
                    # Don't fail registration due to email issues
                    verification_required = False
            
            await self._log_security_event(
                "user_registered",
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                details={"user_type": user_type, "verification_sent": verification_required}
            )
            
            logger.info(f"User registered successfully: {username}")
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user_id": str(user_id),  # Ensure user_id is always a string
                "username": username,
                "email": email,
                "api_key": api_key,
                "verification_required": verification_required
            }
            
        except DuplicateKeyError as e:
            error_msg = "User already exists"
            if "username" in str(e):
                error_msg = "Username already exists"
            elif "email" in str(e):
                error_msg = "Email already exists"
            
            await self._log_security_event(
                "registration_failed",
                ip_address=ip_address,
                details={"error": error_msg, "username": username, "email": email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": error_msg}
            )
        
        except Exception as e:
            logger.error(f"Registration failed for {username}: {e}")
            
            await self._log_security_event(
                "registration_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Registration failed due to server error"}
            )
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate user and create session"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Find user by email
            user = await users_collection.find_one({"email": email.lower()})
            
            if not user:
                await self._log_security_event(
                    "login_failed",
                    ip_address=ip_address,
                    details={"reason": "user_not_found", "email": email}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if user is active
            if not user.get("is_active", True):
                await self._log_security_event(
                    "login_failed",
                    user_id=user["_id"],
                    username=user["username"],
                    ip_address=ip_address,
                    details={"reason": "account_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Account is inactive"}
                )
            
            # Check if account is locked
            locked_until = user.get("locked_until")
            if locked_until and locked_until > datetime.now():
                await self._log_security_event(
                    "login_failed",
                    user_id=user["_id"],
                    username=user["username"],
                    ip_address=ip_address,
                    details={"reason": "account_locked", "locked_until": locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Account locked until {locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, user["password_hash"]):
                # Increment failed attempts
                failed_attempts = user.get("failed_login_attempts", 0) + 1
                update_data = {"failed_login_attempts": failed_attempts}
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    update_data["locked_until"] = datetime.now() + timedelta(hours=1)
                
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": update_data}
                )
                
                await self._log_security_event(
                    "login_failed",
                    user_id=user["_id"],
                    username=user["username"],
                    ip_address=ip_address,
                    details={
                        "reason": "invalid_password",
                        "failed_attempts": failed_attempts
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if password hash needs upgrade
            if password_manager.needs_rehash(user["password_hash"]):
                new_hash = password_manager.hash_password(password)
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"password_hash": new_hash}}
                )
                
                await self._log_security_event(
                    "password_hash_upgraded",
                    user_id=user["_id"],
                    username=user["username"],
                    ip_address=ip_address,
                    details={"from": "bcrypt", "to": "argon2id"}
                )
            
            # Reset failed attempts and update login info
            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "failed_login_attempts": 0,
                    "last_login": datetime.now(),
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }}
            )
            
            # Create session
            session_token = token_manager.generate_session_token()
            refresh_token = token_manager.generate_session_token()
            
            expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            refresh_expires_at = datetime.now() + timedelta(days=self.refresh_token_duration_days)
            
            sessions_collection = await get_mongodb_collection('user_sessions')
            session_doc = {
                "_id": MongoDBUtils.generate_object_id(),
                "user_id": user["_id"],
                "session_token": session_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "refresh_expires_at": refresh_expires_at,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "is_active": True,
                "created_at": datetime.now(),
                "last_used": datetime.now()
            }
            
            await sessions_collection.insert_one(session_doc)
            
            await self._log_security_event(
                "login_successful",
                user_id=user["_id"],
                username=user["username"],
                ip_address=ip_address,
                details={"session_id": session_doc["_id"]}
            )
            
            logger.info(f"User logged in successfully: {user['username']}")
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": str(user["_id"]),  # Ensure id is always a string
                    "username": user["username"],
                    "name": user["name"],
                    "email": user["email"],
                    "user_type": user["user_type"],
                    "subscription_plan": user["subscription_plan"],
                    "is_verified": user.get("is_verified", False)
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
                "login_error",
                ip_address=ip_address,
                details={"error": str(e), "email": email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Authentication failed due to server error"}
            )
    
    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user"""
        
        try:
            sessions_collection = await get_mongodb_collection('user_sessions')
            
            # Find active session
            session = await sessions_collection.find_one({
                "session_token": session_token,
                "is_active": True,
                "expires_at": {"$gt": datetime.now()}
            })
            
            if not session:
                return None
            
            # Get user
            users_collection = await get_mongodb_collection('users')
            user = await users_collection.find_one({"_id": session["user_id"]})
            
            if not user or not user.get("is_active", True):
                return None
            
            # Update session and user activity
            await sessions_collection.update_one(
                {"_id": session["_id"]},
                {"$set": {"last_used": datetime.now()}}
            )
            
            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_activity": datetime.now()}}
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            user = await users_collection.find_one({
                "api_key": api_key,
                "is_active": True
            })
            
            if user:
                # Check if email verification is required for API access
                if settings.email_verification_enabled and not user.get("is_verified", False):
                    logger.warning(f"API access denied for unverified user: {user['username']}")
                    return None
                
                # Update last activity
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_activity": datetime.now()}}
                )
            
            return user
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return None
    
    async def regenerate_api_key(self, user_id: str) -> Dict[str, Any]:
        """Regenerate API key for user"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Get user
            user = await users_collection.find_one({"_id": user_id})
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "User not found"}
                )
            
            # Check if email verification is required
            if settings.email_verification_enabled and not user.get("is_verified", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"message": "Email verification required to access API key"}
                )
            
            # Generate new API key
            old_api_key = user["api_key"]
            new_api_key = await self._generate_unique_api_key()
            
            await users_collection.update_one(
                {"_id": user_id},
                {"$set": {
                    "api_key": new_api_key,
                    "updated_at": datetime.now()
                }}
            )
            
            await self._log_security_event(
                "api_key_regenerated",
                user_id=user_id,
                username=user["username"],
                details={"old_key_prefix": old_api_key[:10], "new_key_prefix": new_api_key[:10]}
            )
            
            return {
                "success": True,
                "message": "API key regenerated successfully",
                "api_key": new_api_key
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key regeneration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "API key regeneration failed"}
            )
    
    async def get_api_key(self, user_id: str) -> Dict[str, Any]:
        """Get user's API key with verification check"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            user = await users_collection.find_one({"_id": user_id})
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "User not found"}
                )
            
            # Check if email verification is required
            if settings.email_verification_enabled and not user.get("is_verified", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"message": "Email verification required to access API key"}
                )
            
            return {
                "success": True,
                "message": "API key retrieved successfully",
                "api_key": user["api_key"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get API key for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to retrieve API key"}
            )
    
    async def _validate_registration_data(
        self,
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
            users_collection = await get_mongodb_collection('users')
            existing_user = await users_collection.find_one({"username": username})
            if existing_user:
                errors.append("Username already exists")
        
        # Validate name
        if not name or len(name) < 2:
            errors.append("Name must be at least 2 characters long")
        elif len(name) > 100:
            errors.append("Name must be less than 100 characters")
        
        # Validate email
        try:
            validated_email = validate_email(email, check_deliverability=False)
            email = validated_email.email
        except EmailNotValidError:
            errors.append("Invalid email format")
        
        # Check if email exists
        if email:
            users_collection = await get_mongodb_collection('users')
            existing_user = await users_collection.find_one({"email": email.lower()})
            if existing_user:
                errors.append("Email already exists")
        
        # Validate password (with username and email check)
        is_strong, password_errors = password_manager.validate_password_strength(
            password, 
            username=username, 
            email=email
        )
        if not is_strong:
            errors.extend(password_errors)
        
        return errors
    
    async def _generate_unique_api_key(self) -> str:
        """Generate unique API key"""
        max_attempts = 10
        users_collection = await get_mongodb_collection('users')
        
        for _ in range(max_attempts):
            api_key = token_manager.generate_api_key()
            
            # Check if key already exists
            existing_user = await users_collection.find_one({"api_key": api_key})
            
            if not existing_user:
                return api_key
        
        raise Exception("Failed to generate unique API key")
    
    async def _log_security_event(
        self,
        event_type: str,
        user_id: str = None,
        username: str = None,
        ip_address: str = None,
        details: dict = None,
        severity: str = "info"
    ):
        """Log security event to MongoDB"""
        try:
            security_collection = await get_mongodb_collection('security_logs')
            
            event_doc = {
                "_id": MongoDBUtils.generate_object_id(),
                "event_type": event_type,
                "user_id": user_id,
                "username": username,
                "ip_address": ip_address,
                "user_agent": None,  # Can be added if needed
                "details": details or {},
                "severity": severity,
                "timestamp": datetime.now()
            }
            
            await security_collection.insert_one(event_doc)
            
        except Exception as e:
            # Don't let logging failures break the main operation
            logger.error(f"Failed to log security event: {e}")


# Global service instance
mongodb_user_service = MongoDBUserService()