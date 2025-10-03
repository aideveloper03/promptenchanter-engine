#!/usr/bin/env python3
"""
Test script to verify user registration and API integration fixes
"""
import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, './app')

from app.services.mongodb_user_service import mongodb_user_service
from app.services.email_service import email_service
from app.database.mongodb import mongodb_manager, get_mongodb_collection
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def test_mongodb_connection():
    """Test MongoDB connection"""
    print("🔗 Testing MongoDB connection...")
    
    try:
        connected = await mongodb_manager.connect()
        if connected:
            print("✅ MongoDB connection successful")
            
            # Test health check
            health = await mongodb_manager.health_check()
            if health:
                print("✅ MongoDB health check passed")
            else:
                print("❌ MongoDB health check failed")
                return False
        else:
            print("❌ MongoDB connection failed")
            return False
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return False
    
    return True


async def test_user_registration():
    """Test user registration with proper ID handling"""
    print("\n👤 Testing user registration...")
    
    try:
        # Test data
        test_user = {
            "username": f"testuser_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": "Test User",
            "email": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@gmail.com",
            "password": "TestPassword123!",
            "user_type": "Personal",
            "about_me": "Test user for registration testing",
            "hobbies": "Testing, Debugging",
            "ip_address": "127.0.0.1"
        }
        
        # Register user
        result = await mongodb_user_service.register_user(**test_user)
        
        print(f"Registration result: {json.dumps(result, indent=2, default=str)}")
        
        # Verify result structure
        required_fields = ["success", "message", "user_id", "username", "email", "api_key"]
        for field in required_fields:
            if field not in result:
                print(f"❌ Missing field in registration result: {field}")
                return False
        
        # Verify user_id is a string (not integer)
        user_id = result["user_id"]
        if not isinstance(user_id, str):
            print(f"❌ user_id should be string, got {type(user_id)}: {user_id}")
            return False
        
        print(f"✅ User registered successfully with ID: {user_id}")
        
        # Test user lookup
        users_collection = await get_mongodb_collection('users')
        user_doc = await users_collection.find_one({"_id": user_id})
        
        if user_doc:
            print("✅ User document found in database")
            print(f"   Username: {user_doc['username']}")
            print(f"   Email: {user_doc['email']}")
            print(f"   User Type: {user_doc['user_type']}")
            print(f"   Credits: {user_doc.get('credits', {})}")
            print(f"   Limits: {user_doc.get('limits', {})}")
        else:
            print("❌ User document not found in database")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ User registration failed: {e}")
        traceback.print_exc()
        return False


async def test_email_service():
    """Test email service configuration"""
    print("\n📧 Testing email service...")
    
    try:
        # Check SMTP configuration
        smtp_configured = bool(
            settings.smtp_host and 
            settings.smtp_username and 
            settings.smtp_password
        )
        
        print(f"SMTP configured: {smtp_configured}")
        print(f"Email verification enabled: {settings.email_verification_enabled}")
        
        if settings.email_verification_enabled and not smtp_configured:
            print("⚠️  Email verification is enabled but SMTP is not configured")
            print("   This will not cause registration to fail (graceful degradation)")
        
        # Test email service initialization
        if smtp_configured:
            print("✅ Email service is properly configured")
        else:
            print("⚠️  Email service not configured (will skip email verification)")
        
        return True
        
    except Exception as e:
        print(f"❌ Email service test failed: {e}")
        return False


async def test_api_key_validation():
    """Test API key validation"""
    print("\n🔑 Testing API key validation...")
    
    try:
        # Temporarily disable email verification for testing
        original_email_verification = settings.email_verification_enabled
        settings.email_verification_enabled = False
        # Create a test user first
        test_user = {
            "username": f"apitest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": "API Test User",
            "email": f"apitest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@gmail.com",
            "password": "TestPassword123!",
            "user_type": "Personal",
            "ip_address": "127.0.0.1"
        }
        
        registration_result = await mongodb_user_service.register_user(**test_user)
        api_key = registration_result["api_key"]
        
        print(f"Testing API key: {api_key[:10]}...")
        
        # Validate API key
        user = await mongodb_user_service.validate_api_key(api_key)
        
        if user:
            print("✅ API key validation successful")
            print(f"   User ID: {user['_id']}")
            print(f"   Username: {user['username']}")
            print(f"   Is Active: {user.get('is_active', False)}")
            print(f"   Is Verified: {user.get('is_verified', False)}")
        else:
            print("❌ API key validation failed")
            return False
        
        # Test invalid API key
        invalid_user = await mongodb_user_service.validate_api_key("invalid-key")
        if invalid_user is None:
            print("✅ Invalid API key correctly rejected")
        else:
            print("❌ Invalid API key was accepted")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API key validation test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        # Restore original email verification setting
        settings.email_verification_enabled = original_email_verification


async def test_user_authentication():
    """Test user authentication flow"""
    print("\n🔐 Testing user authentication...")
    
    try:
        # Create a test user
        test_user = {
            "username": f"authtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": "Auth Test User",
            "email": f"authtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}@gmail.com",
            "password": "TestPassword123!",
            "user_type": "Personal",
            "ip_address": "127.0.0.1"
        }
        
        registration_result = await mongodb_user_service.register_user(**test_user)
        print(f"Created test user: {registration_result['username']}")
        
        # Test authentication
        auth_result = await mongodb_user_service.authenticate_user(
            email=test_user["email"],
            password=test_user["password"],
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        print(f"Authentication result: {json.dumps(auth_result, indent=2, default=str)}")
        
        # Verify authentication result structure
        required_fields = ["success", "message", "user", "session"]
        for field in required_fields:
            if field not in auth_result:
                print(f"❌ Missing field in auth result: {field}")
                return False
        
        # Verify user info structure
        user_info = auth_result["user"]
        user_required_fields = ["id", "username", "name", "email", "user_type"]
        for field in user_required_fields:
            if field not in user_info:
                print(f"❌ Missing field in user info: {field}")
                return False
        
        # Verify user ID is string
        if not isinstance(user_info["id"], str):
            print(f"❌ User ID should be string, got {type(user_info['id'])}")
            return False
        
        print("✅ User authentication successful")
        
        # Test session validation
        session_token = auth_result["session"]["session_token"]
        session_user = await mongodb_user_service.validate_session(session_token)
        
        if session_user:
            print("✅ Session validation successful")
        else:
            print("❌ Session validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ User authentication test failed: {e}")
        traceback.print_exc()
        return False


async def test_database_indexes():
    """Test database indexes are created properly"""
    print("\n📊 Testing database indexes...")
    
    try:
        users_collection = await get_mongodb_collection('users')
        
        # Get collection indexes
        indexes = await users_collection.list_indexes().to_list(None)
        index_names = [idx['name'] for idx in indexes]
        
        print(f"Found indexes: {index_names}")
        
        # Check for required indexes
        required_indexes = ['username_1', 'email_1', 'api_key_1']
        missing_indexes = []
        
        for required_idx in required_indexes:
            if required_idx not in index_names:
                missing_indexes.append(required_idx)
        
        if missing_indexes:
            print(f"⚠️  Missing indexes: {missing_indexes}")
        else:
            print("✅ All required indexes are present")
        
        return True
        
    except Exception as e:
        print(f"❌ Database indexes test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting PromptEnchanter User Management Tests")
    print("=" * 60)
    
    tests = [
        ("MongoDB Connection", test_mongodb_connection),
        ("User Registration", test_user_registration),
        ("Email Service", test_email_service),
        ("API Key Validation", test_api_key_validation),
        ("User Authentication", test_user_authentication),
        ("Database Indexes", test_database_indexes),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! User management system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)