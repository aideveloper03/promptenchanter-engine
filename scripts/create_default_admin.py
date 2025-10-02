#!/usr/bin/env python3
"""
Create default admin user on first startup
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import get_db_session_context
from app.services.admin_service import admin_service
from app.config.settings import get_settings
from app.utils.logger import get_logger
from sqlalchemy import select
from app.database.models import Admin

logger = get_logger(__name__)
settings = get_settings()


async def create_default_admin():
    """Create default admin user if no admin exists"""
    
    try:
        async with get_db_session_context() as session:
            # Check if any admin exists
            result = await session.execute(select(Admin))
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                logger.info("Admin user already exists. Skipping default admin creation.")
                return False
            
            # Create default admin
            logger.info("No admin users found. Creating default admin user...")
            
            result = await admin_service.create_admin(
                session=session,
                username=settings.default_admin_username,
                name=settings.default_admin_name,
                email=settings.default_admin_email,
                password=settings.default_admin_password,
                is_super_admin=True,
                permissions=[
                    "user_management",
                    "admin_management", 
                    "system_monitoring",
                    "security_logs",
                    "support_staff_management",
                    "system_configuration"
                ],
                created_by="system"
            )
            
            logger.info(f"Default admin user created successfully: {settings.default_admin_username}")
            logger.info("IMPORTANT: Please change the default admin password after first login!")
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to create default admin user: {e}")
        return False


async def main():
    """Main function"""
    
    print("PromptEnchanter - Default Admin Creation")
    print("=" * 50)
    
    success = await create_default_admin()
    
    if success:
        print(f"✅ Default admin user created: {settings.default_admin_username}")
        print(f"📧 Email: {settings.default_admin_email}")
        print(f"🔑 Password: {settings.default_admin_password}")
        print("")
        print("⚠️  SECURITY WARNING:")
        print("   Please change the default password immediately after first login!")
        print("   Access the admin panel at: /v1/admin-panel/login")
    else:
        print("ℹ️  Admin user already exists or creation failed.")
    
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())