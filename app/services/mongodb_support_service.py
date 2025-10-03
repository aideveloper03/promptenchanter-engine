"""
MongoDB-based support staff management service
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status

from app.database.mongodb import get_mongodb_collection, MongoDBUtils
from app.security.encryption import password_manager, token_manager
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MongoDBSupportService:
    """MongoDB-based service for support staff management"""
    
    def __init__(self):
        self.session_duration_hours = settings.support_session_duration_hours
    
    async def create_support_staff(
        self,
        username: str,
        name: str,
        email: str,
        password: str,
        staff_level: str = "new",
        created_by: str = None
    ) -> Dict[str, Any]:
        """Create a new support staff member"""
        
        try:
            # Validate password strength
            is_strong, errors = password_manager.validate_password_strength(password)
            if not is_strong:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Password does not meet requirements", "errors": errors}
                )
            
            support_collection = await get_mongodb_collection('support_staff')
            
            # Check if staff already exists
            existing_staff = await support_collection.find_one({
                "$or": [
                    {"username": username},
                    {"email": email.lower()}
                ]
            })
            
            if existing_staff:
                if existing_staff["username"] == username:
                    error_msg = "Username already exists"
                else:
                    error_msg = "Email already exists"
                
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"message": error_msg}
                )
            
            # Hash password
            password_hash = password_manager.hash_password(password)
            
            # Generate staff ID
            staff_id = MongoDBUtils.generate_object_id()
            
            # Create support staff document
            staff_doc = {
                "_id": staff_id,
                "username": username,
                "name": name,
                "email": email.lower(),
                "password_hash": password_hash,
                "staff_level": staff_level,
                "is_active": True,
                "last_login": None,
                "failed_login_attempts": 0,
                "locked_until": None,
                "time_created": datetime.now(),
                "created_by": created_by or "system",
                "updated_at": datetime.now()
            }
            
            await support_collection.insert_one(staff_doc)
            
            await self._log_security_event(
                "support_staff_created",
                user_id=staff_id,
                username=username,
                details={
                    "created_by": created_by,
                    "staff_level": staff_level
                }
            )
            
            logger.info(f"Support staff created successfully: {username}")
            
            return {
                "success": True,
                "message": "Support staff created successfully",
                "staff_id": staff_id,
                "username": username,
                "email": email,
                "staff_level": staff_level
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Support staff creation failed for {username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Support staff creation failed due to server error"}
            )
    
    async def authenticate_support_staff(
        self,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate support staff and create session"""
        
        try:
            support_collection = await get_mongodb_collection('support_staff')
            
            # Find staff by username or email
            staff = await support_collection.find_one({
                "$or": [
                    {"username": username},
                    {"email": username.lower()}
                ]
            })
            
            if not staff:
                await self._log_security_event(
                    "support_login_failed",
                    ip_address=ip_address,
                    details={"reason": "staff_not_found", "username": username}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Invalid credentials"}
                )
            
            # Check if staff is active
            if not staff.get("is_active", True):
                await self._log_security_event(
                    "support_login_failed",
                    user_id=staff["_id"],
                    username=staff["username"],
                    ip_address=ip_address,
                    details={"reason": "account_inactive"}
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Support staff account is inactive"}
                )
            
            # Check if account is locked
            locked_until = staff.get("locked_until")
            if locked_until and locked_until > datetime.now():
                await self._log_security_event(
                    "support_login_failed",
                    user_id=staff["_id"],
                    username=staff["username"],
                    ip_address=ip_address,
                    details={"reason": "account_locked", "locked_until": locked_until.isoformat()}
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={"message": f"Support staff account locked until {locked_until}"}
                )
            
            # Verify password
            if not password_manager.verify_password(password, staff["password_hash"]):
                # Increment failed attempts
                failed_attempts = staff.get("failed_login_attempts", 0) + 1
                update_data = {"failed_login_attempts": failed_attempts}
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    update_data["locked_until"] = datetime.now() + timedelta(hours=1)
                
                await support_collection.update_one(
                    {"_id": staff["_id"]},
                    {"$set": update_data}
                )
                
                await self._log_security_event(
                    "support_login_failed",
                    user_id=staff["_id"],
                    username=staff["username"],
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
            await support_collection.update_one(
                {"_id": staff["_id"]},
                {"$set": {
                    "failed_login_attempts": 0,
                    "last_login": datetime.now(),
                    "updated_at": datetime.now()
                }}
            )
            
            # Create session token
            session_token = token_manager.generate_session_token()
            
            await self._log_security_event(
                "support_login_successful",
                user_id=staff["_id"],
                username=staff["username"],
                ip_address=ip_address,
                details={"session_created": True}
            )
            
            logger.info(f"Support staff logged in successfully: {staff['username']}")
            
            return {
                "success": True,
                "message": "Support staff login successful",
                "staff": {
                    "id": staff["_id"],
                    "username": staff["username"],
                    "name": staff["name"],
                    "email": staff["email"],
                    "staff_level": staff.get("staff_level", "new")
                },
                "session_token": session_token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Support staff authentication failed for {username}: {e}")
            
            await self._log_security_event(
                "support_login_error",
                ip_address=ip_address,
                details={"error": str(e), "username": username}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Support staff authentication failed due to server error"}
            )
    
    async def get_support_staff_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str = None,
        staff_level: str = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """Get paginated list of support staff with filtering"""
        
        try:
            support_collection = await get_mongodb_collection('support_staff')
            
            # Build filter
            filter_query = {}
            
            if search:
                filter_query["$or"] = [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"name": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}}
                ]
            
            if staff_level:
                filter_query["staff_level"] = staff_level
            
            if is_active is not None:
                filter_query["is_active"] = is_active
            
            # Get total count
            total_count = await support_collection.count_documents(filter_query)
            
            # Get support staff
            cursor = support_collection.find(filter_query).skip(skip).limit(limit).sort("time_created", -1)
            staff_list = await cursor.to_list(length=limit)
            
            # Format staff for response
            formatted_staff = []
            for staff in staff_list:
                formatted_staff.append({
                    "id": staff["_id"],
                    "username": staff["username"],
                    "name": staff["name"],
                    "email": staff["email"],
                    "staff_level": staff.get("staff_level", "new"),
                    "is_active": staff.get("is_active", True),
                    "time_created": staff["time_created"],
                    "last_login": staff.get("last_login"),
                    "created_by": staff.get("created_by")
                })
            
            return {
                "success": True,
                "staff": formatted_staff,
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "pages": (total_count + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get support staff list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to retrieve support staff list"}
            )
    
    async def update_support_staff(
        self,
        staff_id: str,
        update_data: Dict[str, Any],
        admin_username: str
    ) -> Dict[str, Any]:
        """Update support staff information"""
        
        try:
            support_collection = await get_mongodb_collection('support_staff')
            
            # Get current staff
            staff = await support_collection.find_one({"_id": staff_id})
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Support staff not found"}
                )
            
            # Prepare update
            update_doc = {"updated_at": datetime.now()}
            
            # Handle specific fields
            allowed_fields = [
                "name", "email", "staff_level", "is_active"
            ]
            
            for field in allowed_fields:
                if field in update_data:
                    update_doc[field] = update_data[field]
            
            # Update staff
            result = await support_collection.update_one(
                {"_id": staff_id},
                {"$set": update_doc}
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "No changes made to support staff"}
                )
            
            await self._log_security_event(
                "support_staff_updated_by_admin",
                user_id=staff_id,
                username=staff["username"],
                details={
                    "admin": admin_username,
                    "updated_fields": list(update_doc.keys()),
                    "changes": update_doc
                }
            )
            
            logger.info(f"Support staff {staff['username']} updated by admin {admin_username}")
            
            return {
                "success": True,
                "message": "Support staff updated successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update support staff {staff_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Failed to update support staff"}
            )
    
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
mongodb_support_service = MongoDBSupportService()