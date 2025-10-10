#!/usr/bin/env python3
"""
Comprehensive system test for PromptEnchanter
Tests all major functionality after fixes
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.database import get_db_session_context, init_database
from app.services.user_service import user_service
from app.services.admin_service import admin_service
from app.services.support_staff_service import support_staff_service
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SystemTester:
    """Comprehensive system tester"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        if not success:
            self.failed_tests.append(test_name)
    
    async def test_database_connection(self):
        """Test database connection and initialization"""
        try:
            await init_database()
            async with get_db_session_context() as session:
                # Test basic query
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            
            self.log_test("Database Connection", True, "Database accessible and responding")
            return True
        except Exception as e:
            self.log_test("Database Connection", False, f"Database error: {e}")
            return False
    
    async def test_user_registration(self):
        """Test user registration functionality"""
        try:
            async with get_db_session_context() as session:
                # Test user registration
                result = await user_service.register_user(
                    session=session,
                    username="testuser123",
                    name="Test User",
                    email="testuser@example.com",
                    password="TestPassword123!",
                    user_type="Personal",
                    about_me="Test user for system testing",
                    hobbies="Testing systems",
                    ip_address="127.0.0.1"
                )
                
                if result["success"]:
                    self.log_test("User Registration", True, f"User created with ID: {result['user_id']}")
                    return True
                else:
                    self.log_test("User Registration", False, "Registration failed")
                    return False
                    
        except Exception as e:
            if "already exists" in str(e).lower():
                self.log_test("User Registration", True, "User already exists (expected)")
                return True
            else:
                self.log_test("User Registration", False, f"Registration error: {e}")
                return False
    
    async def test_user_authentication(self):
        """Test user authentication"""
        try:
            async with get_db_session_context() as session:
                # Test user login
                result = await user_service.authenticate_user(
                    session=session,
                    email="testuser@example.com",
                    password="TestPassword123!",
                    ip_address="127.0.0.1",
                    user_agent="SystemTester/1.0"
                )
                
                if result["success"]:
                    self.log_test("User Authentication", True, f"User authenticated: {result['user']['username']}")
                    return True
                else:
                    self.log_test("User Authentication", False, "Authentication failed")
                    return False
                    
        except Exception as e:
            self.log_test("User Authentication", False, f"Authentication error: {e}")
            return False
    
    async def test_admin_creation(self):
        """Test admin creation functionality"""
        try:
            async with get_db_session_context() as session:
                # Test admin creation
                result = await admin_service.create_admin(
                    session=session,
                    username="testadmin",
                    name="Test Admin",
                    email="testadmin@example.com",
                    password="AdminPassword123!",
                    is_super_admin=True,
                    permissions=["user_management", "system_monitoring"],
                    created_by="system_test"
                )
                
                if result["success"]:
                    self.log_test("Admin Creation", True, f"Admin created with ID: {result['admin_id']}")
                    return True
                else:
                    self.log_test("Admin Creation", False, "Admin creation failed")
                    return False
                    
        except Exception as e:
            if "already exists" in str(e).lower():
                self.log_test("Admin Creation", True, "Admin already exists (expected)")
                return True
            else:
                self.log_test("Admin Creation", False, f"Admin creation error: {e}")
                return False
    
    async def test_support_staff_creation(self):
        """Test support staff creation"""
        try:
            async with get_db_session_context() as session:
                # Test support staff creation
                result = await support_staff_service.create_support_staff(
                    session=session,
                    username="testsupport",
                    name="Test Support",
                    email="testsupport@example.com",
                    password="SupportPassword123!",
                    staff_level="support",
                    created_by="system_test"
                )
                
                if result["success"]:
                    self.log_test("Support Staff Creation", True, f"Support staff created with ID: {result['staff_id']}")
                    return True
                else:
                    self.log_test("Support Staff Creation", False, "Support staff creation failed")
                    return False
                    
        except Exception as e:
            if "already exists" in str(e).lower():
                self.log_test("Support Staff Creation", True, "Support staff already exists (expected)")
                return True
            else:
                self.log_test("Support Staff Creation", False, f"Support staff creation error: {e}")
                return False
    
    async def test_settings_configuration(self):
        """Test settings configuration"""
        try:
            # Test that email verification is disabled by default
            if not settings.email_verification_enabled:
                self.log_test("Email Verification Disabled", True, "Email verification is disabled by default")
            else:
                self.log_test("Email Verification Disabled", False, "Email verification should be disabled by default")
            
            # Test that user registration is enabled
            if settings.user_registration_enabled:
                self.log_test("User Registration Enabled", True, "User registration is enabled")
            else:
                self.log_test("User Registration Enabled", False, "User registration should be enabled")
            
            # Test default user settings
            if settings.default_user_credits and settings.default_user_limits:
                self.log_test("Default User Settings", True, "Default user credits and limits configured")
            else:
                self.log_test("Default User Settings", False, "Default user settings not properly configured")
            
            return True
            
        except Exception as e:
            self.log_test("Settings Configuration", False, f"Settings error: {e}")
            return False
    
    async def test_api_key_generation(self):
        """Test API key generation and validation"""
        try:
            async with get_db_session_context() as session:
                # Find a test user
                from sqlalchemy import select
                from app.database.models import User
                
                result = await session.execute(
                    select(User).where(User.username == "testuser123")
                )
                user = result.scalar_one_or_none()
                
                if user and user.api_key:
                    # Test API key validation
                    validated_user = await user_service.validate_api_key(session, user.api_key)
                    if validated_user and validated_user.id == user.id:
                        self.log_test("API Key Generation", True, "API key generated and validated successfully")
                        return True
                    else:
                        self.log_test("API Key Generation", False, "API key validation failed")
                        return False
                else:
                    self.log_test("API Key Generation", False, "No test user found or API key missing")
                    return False
                    
        except Exception as e:
            self.log_test("API Key Generation", False, f"API key error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all system tests"""
        print("🚀 PromptEnchanter System Test Suite")
        print("=" * 50)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔧 Email Verification: {'Enabled' if settings.email_verification_enabled else 'Disabled'}")
        print(f"👥 User Registration: {'Enabled' if settings.user_registration_enabled else 'Disabled'}")
        print("=" * 50)
        
        # Run tests
        tests = [
            self.test_database_connection,
            self.test_settings_configuration,
            self.test_user_registration,
            self.test_user_authentication,
            self.test_admin_creation,
            self.test_support_staff_creation,
            self.test_api_key_generation
        ]
        
        for test in tests:
            await test()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! System is ready for use.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please review the issues above.")
            print("Failed tests:", ", ".join(self.failed_tests))
        
        print("=" * 50)
        
        return failed_tests == 0


async def main():
    """Main test function"""
    tester = SystemTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())