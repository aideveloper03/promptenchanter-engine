"""
Comprehensive test script for MongoDB-based PromptEnchanter system
"""
import asyncio
import json
from datetime import datetime
from app.config.settings import get_settings
from app.database.mongodb import mongodb_manager
from app.services.mongodb_user_service import mongodb_user_service
from app.services.mongodb_admin_service import mongodb_admin_service
from app.services.email_service import email_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def test_mongodb_connection():
    """Test MongoDB connection"""
    print("🔗 Testing MongoDB connection...")
    
    try:
        connected = await mongodb_manager.connect()
        if connected:
            print("✅ MongoDB connection successful!")
            
            # Test health check
            healthy = await mongodb_manager.health_check()
            if healthy:
                print("✅ MongoDB health check passed!")
            else:
                print("❌ MongoDB health check failed!")
                return False
        else:
            print("❌ MongoDB connection failed!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return False


async def test_user_registration():
    """Test user registration with MongoDB"""
    print("\n👤 Testing user registration...")
    
    try:
        # Test user data
        test_user = {
            "username": "testuser_mongo",
            "name": "Test User MongoDB",
            "email": "testuser.mongo@example.com",
            "password": "TestPassword123!",
            "user_type": "Personal",
            "about_me": "Test user for MongoDB",
            "hobbies": "Testing, Development"
        }
        
        result = await mongodb_user_service.register_user(**test_user)
        
        if result["success"]:
            print(f"✅ User registration successful! User ID: {result['user_id']}")
            print(f"   API Key: {result['api_key'][:20]}...")
            print(f"   Verification required: {result['verification_required']}")
            return result
        else:
            print("❌ User registration failed!")
            return None
        
    except Exception as e:
        print(f"❌ User registration error: {e}")
        return None


async def test_user_login(email: str, password: str):
    """Test user login with MongoDB"""
    print("\n🔐 Testing user login...")
    
    try:
        result = await mongodb_user_service.authenticate_user(
            email=email,
            password=password,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        if result["success"]:
            print("✅ User login successful!")
            print(f"   User: {result['user']['username']}")
            print(f"   Session token: {result['session']['session_token'][:20]}...")
            print(f"   Verified: {result['user']['is_verified']}")
            return result
        else:
            print("❌ User login failed!")
            return None
        
    except Exception as e:
        print(f"❌ User login error: {e}")
        return None


async def test_api_key_validation(api_key: str):
    """Test API key validation"""
    print("\n🔑 Testing API key validation...")
    
    try:
        user = await mongodb_user_service.validate_api_key(api_key)
        
        if user:
            print("✅ API key validation successful!")
            print(f"   User: {user['username']}")
            print(f"   Verified: {user.get('is_verified', False)}")
            return user
        else:
            print("❌ API key validation failed!")
            return None
        
    except Exception as e:
        print(f"❌ API key validation error: {e}")
        return None


async def test_email_verification(user_id: str, email: str, name: str):
    """Test email verification system"""
    print("\n📧 Testing email verification...")
    
    try:
        # Send verification email
        result = await email_service.send_verification_email(user_id, email, name)
        
        if result["success"]:
            print("✅ Verification email sent successfully!")
            print(f"   Expires at: {result.get('expires_at', 'N/A')}")
            
            # For testing, we'll simulate OTP verification with a dummy code
            # In real scenario, user would get the OTP from email
            print("\n🔍 Simulating OTP verification (would normally come from email)...")
            
            # Get the OTP from database for testing
            verification_collection = await mongodb_manager.get_collection('email_verification')
            verification_doc = await verification_collection.find_one({
                "user_id": user_id,
                "email": email,
                "verified": False
            })
            
            if verification_doc:
                otp_code = verification_doc["otp_code"]
                print(f"   Test OTP code: {otp_code}")
                
                # Verify the OTP
                verify_result = await email_service.verify_email_otp(user_id, email, otp_code)
                
                if verify_result["success"]:
                    print("✅ Email verification successful!")
                    return True
                else:
                    print(f"❌ Email verification failed: {verify_result['message']}")
                    return False
            else:
                print("❌ No verification record found!")
                return False
        else:
            print(f"❌ Failed to send verification email: {result['message']}")
            return False
        
    except Exception as e:
        print(f"❌ Email verification error: {e}")
        return False


async def test_admin_creation():
    """Test admin user creation"""
    print("\n👑 Testing admin creation...")
    
    try:
        admin_data = {
            "username": "testadmin_mongo",
            "name": "Test Admin MongoDB",
            "email": "testadmin.mongo@example.com",
            "password": "AdminPassword123!",
            "is_super_admin": True,
            "permissions": ["user_management", "system_config"],
            "created_by": "test_script"
        }
        
        result = await mongodb_admin_service.create_admin(**admin_data)
        
        if result["success"]:
            print(f"✅ Admin creation successful! Admin ID: {result['admin_id']}")
            return result
        else:
            print("❌ Admin creation failed!")
            return None
        
    except Exception as e:
        print(f"❌ Admin creation error: {e}")
        return None


async def test_admin_login(username: str, password: str):
    """Test admin login"""
    print("\n🔐 Testing admin login...")
    
    try:
        result = await mongodb_admin_service.authenticate_admin(
            username=username,
            password=password,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        if result["success"]:
            print("✅ Admin login successful!")
            print(f"   Admin: {result['admin']['username']}")
            print(f"   Super admin: {result['admin']['is_super_admin']}")
            return result
        else:
            print("❌ Admin login failed!")
            return None
        
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return None


async def test_user_management():
    """Test admin user management functions"""
    print("\n👥 Testing user management...")
    
    try:
        # Get users list
        users_result = await mongodb_admin_service.get_users_list(limit=10)
        
        if users_result["success"]:
            print(f"✅ Users list retrieved! Total users: {users_result['pagination']['total']}")
            
            if users_result["users"]:
                first_user = users_result["users"][0]
                print(f"   First user: {first_user['username']} ({first_user['email']})")
                return users_result
            else:
                print("   No users found in database")
                return users_result
        else:
            print("❌ Failed to get users list!")
            return None
        
    except Exception as e:
        print(f"❌ User management error: {e}")
        return None


async def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    try:
        users_collection = await mongodb_manager.get_collection('users')
        admins_collection = await mongodb_manager.get_collection('admins')
        sessions_collection = await mongodb_manager.get_collection('user_sessions')
        verification_collection = await mongodb_manager.get_collection('email_verification')
        
        # Delete test users and related data
        test_users = await users_collection.find({
            "email": {"$regex": ".*mongo@example.com"}
        }).to_list(length=None)
        
        for user in test_users:
            await sessions_collection.delete_many({"user_id": user["_id"]})
            await verification_collection.delete_many({"user_id": user["_id"]})
        
        users_deleted = await users_collection.delete_many({
            "email": {"$regex": ".*mongo@example.com"}
        })
        
        # Delete test admins
        admins_deleted = await admins_collection.delete_many({
            "email": {"$regex": ".*mongo@example.com"}
        })
        
        print(f"✅ Cleanup completed!")
        print(f"   Users deleted: {users_deleted.deleted_count}")
        print(f"   Admins deleted: {admins_deleted.deleted_count}")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")


async def run_comprehensive_test():
    """Run comprehensive MongoDB system test"""
    print("🚀 Starting MongoDB PromptEnchanter System Test")
    print("=" * 60)
    
    # Test MongoDB connection
    if not await test_mongodb_connection():
        print("\n❌ MongoDB connection failed. Aborting tests.")
        return
    
    # Test user registration
    user_result = await test_user_registration()
    if not user_result:
        print("\n❌ User registration failed. Aborting tests.")
        return
    
    user_id = user_result["user_id"]
    api_key = user_result["api_key"]
    email = "testuser.mongo@example.com"
    password = "TestPassword123!"
    name = "Test User MongoDB"
    
    # Test user login
    login_result = await test_user_login(email, password)
    if not login_result:
        print("\n❌ User login failed.")
    
    # Test API key validation
    if not await test_api_key_validation(api_key):
        print("\n❌ API key validation failed.")
    
    # Test email verification (if enabled)
    if settings.email_verification_enabled:
        if not await test_email_verification(user_id, email, name):
            print("\n❌ Email verification failed.")
    else:
        print("\n⚠️  Email verification is disabled in settings.")
    
    # Test admin creation
    admin_result = await test_admin_creation()
    if admin_result:
        # Test admin login
        await test_admin_login("testadmin_mongo", "AdminPassword123!")
        
        # Test user management
        await test_user_management()
    
    # Clean up test data
    await cleanup_test_data()
    
    print("\n" + "=" * 60)
    print("🎉 MongoDB System Test Completed!")
    print("\nIf all tests passed, your MongoDB system is working correctly.")
    print("You can now use the MongoDB-based endpoints:")
    print("  - User Management: /v1/users/*")
    print("  - Email Verification: /v1/email/*")
    print("  - Chat Completions: /v1/prompt/*")


async def main():
    """Main function"""
    await run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())