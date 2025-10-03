"""
MongoDB connection and database management for PromptEnchanter
"""
import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.server_api import ServerApi
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MongoDBManager:
    """MongoDB connection and database management"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collections: Dict[str, AsyncIOMotorCollection] = {}
        
    async def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            mongodb_url = getattr(settings, 'mongodb_url', None)
            mongodb_database = getattr(settings, 'mongodb_database', 'promptenchanter')
            
            if not mongodb_url:
                logger.error("MongoDB URL not configured")
                return False
            
            # Create client with server API version
            self.client = AsyncIOMotorClient(
                mongodb_url,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                maxPoolSize=50,
                minPoolSize=10
            )
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB!")
            
            # Get database
            self.database = self.client[mongodb_database]
            
            # Initialize collections
            await self._initialize_collections()
            
            return True
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _initialize_collections(self):
        """Initialize collections and create indexes"""
        try:
            # Define collections
            collection_names = [
                'users', 'deleted_users', 'user_sessions', 'message_logs',
                'admins', 'support_staff', 'security_logs', 'ip_whitelist',
                'api_usage_logs', 'system_config', 'email_verification'
            ]
            
            # Create collections if they don't exist
            existing_collections = await self.database.list_collection_names()
            
            for collection_name in collection_names:
                if collection_name not in existing_collections:
                    await self.database.create_collection(collection_name)
                    logger.info(f"Created collection: {collection_name}")
                
                # Store collection reference
                self.collections[collection_name] = self.database[collection_name]
            
            # Create indexes for better performance
            await self._create_indexes()
            
            logger.info("MongoDB collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Users collection indexes
            users = self.collections['users']
            await users.create_index("username", unique=True)
            await users.create_index("email", unique=True)
            await users.create_index("api_key", unique=True)
            await users.create_index("is_active")
            await users.create_index("is_verified")
            await users.create_index("time_created")
            
            # User sessions indexes
            sessions = self.collections['user_sessions']
            await sessions.create_index("user_id")
            await sessions.create_index("session_token", unique=True)
            await sessions.create_index("refresh_token", unique=True)
            await sessions.create_index("expires_at")
            await sessions.create_index("is_active")
            
            # Message logs indexes
            messages = self.collections['message_logs']
            await messages.create_index("user_id")
            await messages.create_index("username")
            await messages.create_index("email")
            await messages.create_index("timestamp")
            await messages.create_index("model")
            
            # Admins collection indexes
            admins = self.collections['admins']
            await admins.create_index("username", unique=True)
            await admins.create_index("email", unique=True)
            await admins.create_index("is_active")
            
            # Support staff indexes
            support = self.collections['support_staff']
            await support.create_index("username", unique=True)
            await support.create_index("email", unique=True)
            await support.create_index("is_active")
            
            # Security logs indexes
            security = self.collections['security_logs']
            await security.create_index("event_type")
            await security.create_index("user_id")
            await security.create_index("username")
            await security.create_index("ip_address")
            await security.create_index("timestamp")
            await security.create_index("severity")
            
            # API usage logs indexes
            api_usage = self.collections['api_usage_logs']
            await api_usage.create_index("user_id")
            await api_usage.create_index("api_key")
            await api_usage.create_index("endpoint")
            await api_usage.create_index("timestamp")
            await api_usage.create_index("date")
            
            # Email verification indexes
            email_verification = self.collections['email_verification']
            await email_verification.create_index("user_id")
            await email_verification.create_index("email")
            await email_verification.create_index("otp_code")
            await email_verification.create_index("expires_at")
            await email_verification.create_index("created_at")
            
            # System config indexes
            config = self.collections['system_config']
            await config.create_index("key", unique=True)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            # Don't raise here as indexes are for performance, not critical
    
    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get collection by name"""
        if name not in self.collections:
            raise ValueError(f"Collection '{name}' not found")
        return self.collections[name]
    
    async def health_check(self) -> bool:
        """Check MongoDB connection health"""
        try:
            if not self.client:
                return False
            
            # Ping the database
            await self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False


# Global MongoDB manager instance
mongodb_manager = MongoDBManager()


async def get_mongodb_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    if not mongodb_manager.database:
        connected = await mongodb_manager.connect()
        if not connected:
            raise Exception("Failed to connect to MongoDB")
    
    return mongodb_manager.database


async def get_mongodb_collection(name: str) -> AsyncIOMotorCollection:
    """Get MongoDB collection by name"""
    if not mongodb_manager.database:
        connected = await mongodb_manager.connect()
        if not connected:
            raise Exception("Failed to connect to MongoDB")
    
    return mongodb_manager.get_collection(name)


# Utility functions for MongoDB operations
class MongoDBUtils:
    """Utility functions for MongoDB operations"""
    
    @staticmethod
    def serialize_datetime(obj: Any) -> Any:
        """Serialize datetime objects for MongoDB"""
        if isinstance(obj, datetime):
            return obj
        elif isinstance(obj, dict):
            return {k: MongoDBUtils.serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [MongoDBUtils.serialize_datetime(item) for item in obj]
        return obj
    
    @staticmethod
    def prepare_document(data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for MongoDB insertion"""
        # Remove None values
        cleaned_data = {k: v for k, v in data.items() if v is not None}
        
        # Handle datetime serialization
        return MongoDBUtils.serialize_datetime(cleaned_data)
    
    @staticmethod
    def generate_object_id() -> str:
        """Generate a new MongoDB ObjectId as string"""
        from bson import ObjectId
        return str(ObjectId())


# MongoDB document schemas for validation
class DocumentSchemas:
    """Document schemas for MongoDB collections"""
    
    USER_SCHEMA = {
        "username": str,
        "name": str,
        "email": str,
        "password_hash": str,
        "about_me": str,
        "hobbies": str,
        "user_type": str,
        "time_created": datetime,
        "subscription_plan": str,
        "credits": dict,
        "limits": dict,
        "access_rtype": list,
        "level": str,
        "additional_notes": str,
        "api_key": str,
        "is_active": bool,
        "is_verified": bool,
        "email_verification_token": str,
        "password_reset_token": str,
        "password_reset_expires": datetime,
        "last_login": datetime,
        "failed_login_attempts": int,
        "locked_until": datetime,
        "created_at": datetime,
        "updated_at": datetime,
        "last_activity": datetime
    }
    
    EMAIL_VERIFICATION_SCHEMA = {
        "user_id": str,
        "email": str,
        "otp_code": str,
        "expires_at": datetime,
        "created_at": datetime,
        "attempts": int,
        "verified": bool,
        "resend_count": int,
        "last_resend": datetime
    }