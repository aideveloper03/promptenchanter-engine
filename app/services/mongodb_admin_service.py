"""
MongoDB-based admin management service for user administration and system control
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status

from app.database.mongodb import get_mongodb_collection, MongoDBUtils
from app.security.encryption import (
    password_manager, 
    token_manager, 
    encryption_manager
)
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MongoDBAdminService:
    """MongoDB-based service for admin management operations"""
    
    def __init__(self):
        self.session_duration_hours = settings.admin_session_duration_hours
        self.refresh_token_duration_days = 7  # Shorter for admin sessions
    
    async def create_admin(
        self,
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
            
            admins_collection = await get_mongodb_collection('admins')
            
            # Check if admin already exists
            existing_admin = await admins_collection.find_one({
                "$or": [
                    {"username": username},
                    {"email": email.lower()}
                ]
            })
            
            if existing_admin:
                if existing_admin["username"] == username:
                    error_msg = "Username already exists"
                else:
                    error_msg = "Email already exists"
                
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"message": error_msg}
                )
            
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Generate admin ID
            admin_id = MongoDBUtils.generate_object_id()
            
            # Create admin document
            admin_doc = {
                "_id": admin_id,
                "username": username,
                "name": name,
                "email": email.lower(),
                "password_hash": password_hash,
                "is_super_admin": is_super_admin,
                "permissions": permissions or [],
                "is_active": True,
                "last_login": None,
                "failed_login_attempts": 0,
                "locked_until": None,
                "created_at": datetime.now(),
                "created_by": created_by,
                "updated_at": datetime.now()
            }
            
            await admins_collection.insert_one(admin_doc)
            
            await self._log_security_event(
                "admin_created",
                admin_id=admin_id,
                username=username,
                details={
                    "created_by": created_by,
                    "is_super_admin": is_super_admin,
                    "permissions": permissions or []
                }
            )
            
            logger.info(f"Admin created successfully: {username}")
            
            return {
                "success": True,
                "message": "Admin created successfully",
                "admin_id": admin_id,
                "username": username,
                "email": email,
                "is_super_admin": is_super_admin
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin creation failed for {username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Admin creation failed due to server error"}
            )
    
    async def authenticate_admin(
        self,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate admin and create session"""
        
        try:
            admins_collection = await get_mongodb_collection('admins')
            
            # Find admin by username or email
            admin = await admins_collection.find_one({
                "$or": [
                    {"username": username},
                    {"email": username.lower()}
                ]
            })
            
            if not admin:
                await self._log_security_event(
                    "admin_login_failed",
                    ip_address=ip_address,
                    details={"reason": "admin_not_found", "username": username}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if admin is active
            if not admin.get("is_active", True):
                await self._log_security_event(
                    "admin_login_failed",
                    admin_id=admin["_id"],
                    username=admin["username"],
                    ip_address=ip_address,
                    details={"reason": "account_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Admin account is inactive"}
                )
            
            # Check if account is locked
            locked_until = admin.get("locked_until")
            if locked_until and locked_until > datetime.now():
                await self._log_security_event(
                    "admin_login_failed",
                    admin_id=admin["_id"],
                    username=admin["username"],
                    ip_address=ip_address,
                    details={"reason": "account_locked", "locked_until": locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Admin account locked until {locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, admin["password_hash"]):
                # Increment failed attempts
                failed_attempts = admin.get("failed_login_attempts", 0) + 1
                update_data = {"failed_login_attempts": failed_attempts}
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    update_data["locked_until"] = datetime.now() + timedelta(hours=1)
                
                await admins_collection.update_one(
                    {"_id": admin["_id"]},
                    {"$set": update_data}
                )
                
                await self._log_security_event(
                    "admin_login_failed",
                    admin_id=admin["_id"],
                    username=admin["username"],
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
            
            # Reset failed attempts and update login info
            await admins_collection.update_one(
                {"_id": admin["_id"]},
                {"$set": {
                    "failed_login_attempts": 0,
                    "last_login": datetime.now(),
                    "updated_at": datetime.now()
                }}
            )
            
            # Create session token
            session_token = token_manager.generate_session_token()
            
            await self._log_security_event(
                "admin_login_successful",
                admin_id=admin["_id"],
                username=admin["username"],
                ip_address=ip_address,
                details={"session_created": True}
            )
            
            logger.info(f"Admin logged in successfully: {admin['username']}")
            
            return {
                "success": True,
                "message": "Admin login successful",
                "admin": {
                    "id": admin["_id"],
                    "username": admin["username"],
                    "name": admin["name"],
                    "email": admin["email"],
                    "is_super_admin": admin.get("is_super_admin", False),
                    "permissions": admin.get("permissions", [])
                },
                "session_token": session_token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin authentication failed for {username}: {e}")
            
            await self._log_security_event(
                "admin_login_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Admin authentication failed due to server error"}
            )
    
    async def get_users_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str = None,
        user_type: str = None,
        is_active: bool = None,
        is_verified: bool = None
    ) -> Dict[str, Any]:
        """Get paginated list of users with filtering"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Build filter
            filter_query = {}
            
            if search:
                filter_query["$or"] = [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"name": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}}
                ]
            
            if user_type:
                filter_query["user_type"] = user_type
            
            if is_active is not None:
                filter_query["is_active"] = is_active
            
            if is_verified is not None:
                filter_query["is_verified"] = is_verified
            
            # Get total count
            total_count = await users_collection.count_documents(filter_query)
            
            # Get users
            cursor = users_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
            users = await cursor.to_list(length=limit)
            
            # Format users for response
            formatted_users = []
            for user in users:
                formatted_users.append({
                    "id": user["_id"],
                    "username": user["username"],
                    "name": user["name"],
                    "email": user["email"],
                    "user_type": user["user_type"],
                    "subscription_plan": user["subscription_plan"],
                    "credits": user.get("credits", {}),
                    "limits": user.get("limits", {}),
                    "level": user["level"],
                    "is_active": user.get("is_active", True),
                    "is_verified": user.get("is_verified", False),
                    "time_created": user["time_created"],
                    "last_login": user.get("last_login"),
                    "last_activity": user.get("last_activity")
                })
            
            return {
                "success": True,
                "users": formatted_users,
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "pages": (total_count + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get users list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to retrieve users list"}
            )
    
    async def update_user(
        self,
        user_id: str,
        update_data: Dict[str, Any],
        admin_username: str
    ) -> Dict[str, Any]:
        """Update user information"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Get current user
            user = await users_collection.find_one({"_id": user_id})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "User not found"}
                )
            
            # Prepare update
            update_doc = {"updated_at": datetime.now()}
            
            # Handle specific fields
            allowed_fields = [
                "name", "email", "user_type", "subscription_plan", 
                "credits", "limits", "access_rtype", "level", 
                "additional_notes", "is_active", "is_verified"
            ]
            
            for field in allowed_fields:
                if field in update_data:
                    update_doc[field] = update_data[field]
            
            # Update user
            result = await users_collection.update_one(
                {"_id": user_id},
                {"$set": update_doc}
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "No changes made to user"}
                )
            
            await self._log_security_event(
                "user_updated_by_admin",
                user_id=user_id,
                username=user["username"],
                details={
                    "admin": admin_username,
                    "updated_fields": list(update_doc.keys()),
                    "changes": update_doc
                }
            )
            
            logger.info(f"User {user['username']} updated by admin {admin_username}")
            
            return {
                "success": True,
                "message": "User updated successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to update user"}
            )
    
    async def delete_user(
        self,
        user_id: str,
        admin_username: str,
        reason: str = "Deleted by admin"
    ) -> Dict[str, Any]:
        """Delete user account with data archiving"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            deleted_users_collection = await get_mongodb_collection('deleted_users')
            sessions_collection = await get_mongodb_collection('user_sessions')
            messages_collection = await get_mongodb_collection('message_logs')
            
            # Get user
            user = await users_collection.find_one({"_id": user_id})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "User not found"}
                )
            
            # Archive user data
            deleted_user_doc = {
                "_id": f"deleted_{user_id}",
                "original_user_id": user_id,
                "username": user["username"],
                "name": user["name"],
                "email": user["email"],
                "user_type": user["user_type"],
                "time_created": user["time_created"],
                "subscription_plan": user["subscription_plan"],
                "deletion_reason": reason,
                "deleted_at": datetime.now(),
                "deleted_by": admin_username
            }
            
            await deleted_users_collection.insert_one(deleted_user_doc)
            
            # Delete user and related data
            await sessions_collection.delete_many({"user_id": user_id})
            await messages_collection.delete_many({"user_id": user_id})
            await users_collection.delete_one({"_id": user_id})
            
            await self._log_security_event(
                "user_deleted_by_admin",
                user_id=user_id,
                username=user["username"],
                details={
                    "admin": admin_username,
                    "reason": reason
                }
            )
            
            logger.info(f"User {user['username']} deleted by admin {admin_username}")
            
            return {
                "success": True,
                "message": "User deleted successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to delete user"}
            )
    
    async def _log_security_event(
        self,
        event_type: str,
        admin_id: str = None,
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
                "user_id": user_id or admin_id,
                "username": username,
                "ip_address": ip_address,
                "user_agent": None,
                "details": details or {},
                "severity": severity,
                "timestamp": datetime.now()
            }
            
            await security_collection.insert_one(event_doc)
            
        except Exception as e:
            # Don't let logging failures break the main operation
            logger.error(f"Failed to log security event: {e}")


# Global service instance
mongodb_admin_service = MongoDBAdminService()