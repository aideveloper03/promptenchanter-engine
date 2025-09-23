#!/usr/bin/env python3
"""
Complete setup verification script for PromptEnchanter
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.database.database import get_db_session, init_database
from app.database.models import User, Admin, SupportStaff
from app.services.user_service import user_service
from app.services.admin_service import admin_service
from app.config.settings import get_settings
from sqlalchemy import select, func


async def check_database():
    """Check database connectivity and tables"""
    print("🔍 Checking database...")
    
    try:
        # Initialize database
        await init_database()
        print("  ✅ Database initialized successfully")
        
        # Check tables
        async with get_db_session() as session:
            # Count users
            user_count = await session.execute(select(func.count(User.id)))
            user_total = user_count.scalar()
            
            # Count admins
            admin_count = await session.execute(select(func.count(Admin.id)))
            admin_total = admin_count.scalar()
            
            # Count support staff
            staff_count = await session.execute(select(func.count(SupportStaff.id)))
            staff_total = staff_count.scalar()
            
            print(f"  📊 Database statistics:")
            print(f"    - Users: {user_total}")
            print(f"    - Admins: {admin_total}")
            print(f"    - Support Staff: {staff_total}")
            
            if admin_total == 0:
                print("  ⚠️  No admin users found. Run 'python scripts/create_admin.py' first.")
                return False
            
            return True
            
    except Exception as e:
        print(f"  ❌ Database check failed: {e}")
        return False


async def check_configuration():
    """Check configuration settings"""
    print("\n🔧 Checking configuration...")
    
    settings = get_settings()
    
    # Check critical settings
    checks = []
    
    # Database URL
    if settings.database_url:
        print(f"  ✅ Database URL configured: {settings.database_url.split('://')[0]}://...")
        checks.append(True)
    else:
        print("  ❌ Database URL not configured")
        checks.append(False)
    
    # WAPI configuration
    if settings.wapi_url and settings.wapi_key:
        print(f"  ✅ WAPI configured: {settings.wapi_url}")
        checks.append(True)
    else:
        print("  ❌ WAPI not properly configured")
        checks.append(False)
    
    # Secret key
    if settings.secret_key != "your-secret-key-change-in-production":
        print("  ✅ Secret key configured")
        checks.append(True)
    else:
        print("  ⚠️  Using default secret key - change in production!")
        checks.append(True)  # Not critical for development
    
    # Redis
    if settings.redis_url:
        print(f"  ✅ Redis configured: {settings.redis_url}")
        checks.append(True)
    else:
        print("  ⚠️  Redis not configured - will use memory cache")
        checks.append(True)  # Not critical
    
    # Security settings
    security_ok = True
    if settings.firewall_enabled:
        print("  ✅ Firewall enabled")
    else:
        print("  ⚠️  Firewall disabled")
        security_ok = False
    
    if settings.ip_whitelist_enabled:
        print("  ✅ IP whitelisting enabled")
    else:
        print("  ℹ️  IP whitelisting disabled (OK for development)")
    
    checks.append(security_ok)
    
    return all(checks)


async def test_user_registration():
    """Test user registration functionality"""
    print("\n👤 Testing user registration...")
    
    try:
        async with get_db_session() as session:
            # Try to register a test user
            test_username = f"testuser_{int(asyncio.get_event_loop().time())}"
            
            result = await user_service.register_user(
                session=session,
                username=test_username,
                name="Test User",
                email=f"{test_username}@example.com",
                password="TestPass123",
                user_type="Personal"
            )
            
            print(f"  ✅ User registration successful")
            print(f"    - Username: {result['username']}")
            print(f"    - API Key: {result['api_key'][:15]}...")
            
            # Clean up test user
            user_result = await session.execute(
                select(User).where(User.username == test_username)
            )
            test_user = user_result.scalar_one_or_none()
            if test_user:
                await session.delete(test_user)
                await session.commit()
                print("  🧹 Test user cleaned up")
            
            return True
            
    except Exception as e:
        print(f"  ❌ User registration test failed: {e}")
        return False


async def test_admin_login():
    """Test admin functionality"""
    print("\n👑 Testing admin system...")
    
    try:
        async with get_db_session() as session:
            # Check if admin exists
            admin_result = await session.execute(select(Admin).limit(1))
            admin = admin_result.scalar_one_or_none()
            
            if not admin:
                print("  ❌ No admin users found")
                return False
            
            print(f"  ✅ Admin user found: {admin.username}")
            print(f"    - Super Admin: {'Yes' if admin.is_super_admin else 'No'}")
            print(f"    - Created: {admin.created_at}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Admin test failed: {e}")
        return False


async def check_services():
    """Check background services"""
    print("\n🚀 Checking services...")
    
    # Check message logging service
    from app.services.message_logging_service import message_logging_service
    queue_status = message_logging_service.get_queue_status()
    
    if queue_status["is_running"]:
        print("  ✅ Message logging service running")
    else:
        print("  ⚠️  Message logging service not running")
    
    # Check credit reset service
    from app.services.credit_reset_service import credit_reset_service
    credit_status = credit_reset_service.get_status()
    
    if credit_status["is_running"]:
        print("  ✅ Credit reset service running")
        print(f"    - Next reset: {credit_status['next_reset_time']}")
    else:
        print("  ⚠️  Credit reset service not running")
    
    return True


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP VERIFICATION COMPLETE!")
    print("="*60)
    
    print("\n📋 NEXT STEPS:")
    print("\n1. Start the server:")
    print("   python main.py")
    print("   # or for production:")
    print("   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4")
    
    print("\n2. Access the API documentation:")
    print("   http://localhost:8000/docs")
    
    print("\n3. Test the health endpoint:")
    print("   curl http://localhost:8000/health")
    
    print("\n4. Register your first user:")
    print("   curl -X POST 'http://localhost:8000/v1/users/register' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "username": "yourname",')
    print('       "name": "Your Name",')
    print('       "email": "your@email.com",')
    print('       "password": "YourSecurePass123"')
    print("     }'")
    
    print("\n5. Login to admin panel:")
    print("   curl -X POST 'http://localhost:8000/v1/admin-panel/login' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "username": "your-admin-username",')
    print('       "password": "your-admin-password"')
    print("     }'")
    
    print("\n📚 DOCUMENTATION:")
    print("   - User Management Guide: docs/USER_MANAGEMENT_GUIDE.md")
    print("   - Setup Guide: docs/SETUP_GUIDE.md")
    print("   - API Guide: docs/API_GUIDE.md")
    
    print("\n🔒 SECURITY REMINDERS:")
    print("   - Change SECRET_KEY in production")
    print("   - Enable IP_WHITELIST_ENABLED for production")
    print("   - Use PostgreSQL for production databases")
    print("   - Set up HTTPS/SSL in production")
    print("   - Regular database backups")
    
    print("\n" + "="*60)


async def main():
    """Main verification function"""
    print("🔍 PromptEnchanter Setup Verification")
    print("=" * 40)
    
    # Run all checks
    checks = []
    
    checks.append(await check_database())
    checks.append(await check_configuration())
    checks.append(await test_user_registration())
    checks.append(await test_admin_login())
    checks.append(await check_services())
    
    print("\n" + "="*40)
    print("📊 VERIFICATION SUMMARY")
    print("="*40)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ All {total} checks passed!")
        print_next_steps()
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\nPlease address the issues above before proceeding.")
        
        if passed >= total - 1:
            print("\nMost checks passed - you can probably proceed with caution.")
            print_next_steps()
        else:
            print("\nToo many issues found. Please fix configuration and try again.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())