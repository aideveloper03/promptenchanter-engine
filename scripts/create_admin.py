#!/usr/bin/env python3
"""
Script to create the first admin user for PromptEnchanter
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.database.database import get_db_session
from app.services.admin_service import admin_service
from app.security.encryption import password_manager


async def create_first_admin():
    """Create the first admin user"""
    
    print("=== PromptEnchanter Admin Creation ===\n")
    
    # Get admin details
    username = input("Enter admin username: ").strip()
    if not username:
        print("Username cannot be empty!")
        return False
    
    name = input("Enter admin full name: ").strip()
    if not name:
        print("Name cannot be empty!")
        return False
    
    email = input("Enter admin email: ").strip()
    if not email:
        print("Email cannot be empty!")
        return False
    
    while True:
        password = input("Enter admin password: ").strip()
        if not password:
            print("Password cannot be empty!")
            continue
        
        # Validate password strength
        is_strong, errors = password_manager.validate_password_strength(password)
        if not is_strong:
            print("Password does not meet requirements:")
            for error in errors:
                print(f"  - {error}")
            continue
        
        confirm_password = input("Confirm admin password: ").strip()
        if password != confirm_password:
            print("Passwords do not match!")
            continue
        
        break
    
    print("\nCreating admin user...")
    
    try:
        async with get_db_session() as session:
            result = await admin_service.create_admin(
                session=session,
                username=username,
                name=name,
                email=email,
                password=password,
                is_super_admin=True,
                permissions=["all"],
                created_by="system"
            )
        
        print(f"\n✅ Admin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Super Admin: Yes")
        print(f"\nYou can now login to the admin panel using these credentials.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to create admin user: {e}")
        return False


async def main():
    """Main function"""
    
    # Check if database exists and has admin users
    try:
        from app.database.database import init_database
        from app.database.models import Admin
        from sqlalchemy import select, func
        
        # Initialize database
        await init_database()
        
        # Check if any admin users exist
        async with get_db_session() as session:
            result = await session.execute(select(func.count(Admin.id)))
            admin_count = result.scalar()
        
        if admin_count > 0:
            print(f"Database already contains {admin_count} admin user(s).")
            overwrite = input("Do you want to create another admin? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("Exiting...")
                return
        
        success = await create_first_admin()
        
        if success:
            print("\n🎉 Setup complete! You can now start the PromptEnchanter server.")
        else:
            print("\n❌ Setup failed. Please try again.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())