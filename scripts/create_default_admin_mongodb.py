"""
Create default admin user in MongoDB for PromptEnchanter
"""
import asyncio
from app.config.settings import get_settings
from app.database.mongodb import mongodb_manager
from app.services.mongodb_admin_service import mongodb_admin_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def create_default_admin():
    """Create default admin user if none exists"""
    
    try:
        # Connect to MongoDB
        connected = await mongodb_manager.connect()
        if not connected:
            logger.warning("MongoDB not available, skipping admin creation")
            return
        
        # Check if any admin exists
        admins_collection = mongodb_manager.get_collection('admins')
        admin_count = await admins_collection.count_documents({})
        
        if admin_count > 0:
            logger.info("Admin users already exist, skipping default admin creation")
            return
        
        # Create default admin
        admin_data = {
            "username": settings.default_admin_username,
            "name": settings.default_admin_name,
            "email": settings.default_admin_email,
            "password": settings.default_admin_password,
            "is_super_admin": True,
            "permissions": [
                "user_management",
                "system_config",
                "security_logs",
                "api_usage",
                "support_management"
            ],
            "created_by": "system"
        }
        
        result = await mongodb_admin_service.create_admin(**admin_data)
        
        if result["success"]:
            logger.info(f"Default admin user created: {settings.default_admin_username}")
            logger.warning("IMPORTANT: Change the default admin password in production!")
        else:
            logger.error("Failed to create default admin user")
        
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")


async def main():
    """Main function for standalone execution"""
    await create_default_admin()


if __name__ == "__main__":
    asyncio.run(main())