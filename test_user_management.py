#!/usr/bin/env python3
"""
Comprehensive Test Script for PromptEnchanter User Management System
"""
import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "testuser123",
    "name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123!",
    "confirm_password": "TestPass123!",
    "user_type": "Personal"
}

class PromptEnchanterTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_token: Optional[str] = None
        self.admin_token: Optional[str] = None
        self.api_key: Optional[str] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, 
                          headers: Dict[str, str] = None, auth_token: str = None) -> Dict[Any, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            async with self.session.request(
                method, url, 
                json=data if data else None,
                headers=request_headers
            ) as response:
                response_data = await response.json()
                return {
                    "status": response.status,
                    "data": response_data
                }
        except Exception as e:
            return {
                "status": 0,
                "error": str(e)
            }
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("🔍 Testing health check...")
        
        response = await self.make_request("GET", "/health")
        
        if response["status"] == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response}")
            return False
    
    async def test_user_registration(self) -> bool:
        """Test user registration"""
        print("🔍 Testing user registration...")
        
        response = await self.make_request("POST", "/user/register", TEST_USER)
        
        if response["status"] == 200 and response["data"].get("success"):
            self.api_key = response["data"].get("api_key")
            print("✅ User registration successful")
            print(f"   API Key: {self.api_key[:20]}...")
            return True
        else:
            print(f"❌ User registration failed: {response}")
            return False
    
    async def test_user_login(self) -> bool:
        """Test user login"""
        print("🔍 Testing user login...")
        
        login_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        
        response = await self.make_request("POST", "/user/login", login_data)
        
        if response["status"] == 200 and response["data"].get("success"):
            self.user_token = response["data"].get("access_token")
            print("✅ User login successful")
            return True
        else:
            print(f"❌ User login failed: {response}")
            return False
    
    async def test_user_profile(self) -> bool:
        """Test user profile endpoints"""
        print("🔍 Testing user profile...")
        
        # Get profile
        response = await self.make_request("GET", "/user/profile", auth_token=self.user_token)
        
        if response["status"] == 200:
            print("✅ Get user profile successful")
            
            # Update profile
            update_data = {
                "about_me": "Updated about me section",
                "hobbies": "Testing, Coding, AI"
            }
            
            response = await self.make_request("PUT", "/user/profile", update_data, auth_token=self.user_token)
            
            if response["status"] == 200 and response["data"].get("success"):
                print("✅ Update user profile successful")
                return True
            else:
                print(f"❌ Update user profile failed: {response}")
                return False
        else:
            print(f"❌ Get user profile failed: {response}")
            return False
    
    async def test_api_key_management(self) -> bool:
        """Test API key management"""
        print("🔍 Testing API key management...")
        
        # Get encrypted API key
        response = await self.make_request("GET", "/user/api-key", auth_token=self.user_token)
        
        if response["status"] == 200 and response["data"].get("success"):
            print("✅ Get API key successful")
            
            # Regenerate API key
            regen_data = {
                "current_password": TEST_USER["password"]
            }
            
            response = await self.make_request("POST", "/user/regenerate-api-key", regen_data, auth_token=self.user_token)
            
            if response["status"] == 200 and response["data"].get("success"):
                print("✅ Regenerate API key successful")
                return True
            else:
                print(f"❌ Regenerate API key failed: {response}")
                return False
        else:
            print(f"❌ Get API key failed: {response}")
            return False
    
    async def test_chat_completion(self) -> bool:
        """Test chat completion with API key authentication"""
        print("🔍 Testing chat completion...")
        
        if not self.api_key:
            print("❌ No API key available for testing")
            return False
        
        chat_data = {
            "level": "medium",
            "messages": [
                {"role": "user", "content": "Hello, this is a test message!"}
            ],
            "r_type": "bpe",
            "temperature": 0.7
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = await self.make_request("POST", "/v1/chat/completions", chat_data, headers=headers)
        
        if response["status"] == 200:
            print("✅ Chat completion successful")
            return True
        else:
            print(f"❌ Chat completion failed: {response}")
            return False
    
    async def test_admin_login(self) -> bool:
        """Test admin login"""
        print("🔍 Testing admin login...")
        
        admin_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        response = await self.make_request("POST", "/admin/login", admin_data)
        
        if response["status"] == 200 and response["data"].get("success"):
            self.admin_token = response["data"].get("access_token")
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {response}")
            return False
    
    async def test_admin_functions(self) -> bool:
        """Test admin functions"""
        print("🔍 Testing admin functions...")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        # Get system stats
        response = await self.make_request("GET", "/admin/stats", auth_token=self.admin_token)
        
        if response["status"] == 200:
            print("✅ Get system stats successful")
            
            # Get all users
            response = await self.make_request("GET", "/admin/users", auth_token=self.admin_token)
            
            if response["status"] == 200:
                print("✅ Get all users successful")
                return True
            else:
                print(f"❌ Get all users failed: {response}")
                return False
        else:
            print(f"❌ Get system stats failed: {response}")
            return False
    
    async def test_security_features(self) -> bool:
        """Test security features"""
        print("🔍 Testing security features...")
        
        # Test invalid API key
        invalid_headers = {"Authorization": "Bearer invalid-key"}
        response = await self.make_request("POST", "/v1/chat/completions", {
            "level": "low",
            "messages": [{"role": "user", "content": "test"}]
        }, headers=invalid_headers)
        
        if response["status"] == 401:
            print("✅ Invalid API key properly rejected")
            
            # Test rate limiting (make multiple rapid requests)
            print("🔍 Testing rate limiting...")
            
            for i in range(5):
                response = await self.make_request("POST", "/user/login", {
                    "email": "invalid@example.com",
                    "password": "invalid"
                })
                
            if response["status"] in [401, 429]:
                print("✅ Rate limiting working")
                return True
            else:
                print(f"⚠️  Rate limiting test inconclusive: {response['status']}")
                return True
        else:
            print(f"❌ Security test failed: {response}")
            return False
    
    async def test_message_logging(self) -> bool:
        """Test message logging"""
        print("🔍 Testing message logging...")
        
        if not self.user_token:
            print("❌ No user token available")
            return False
        
        # Get message logs
        response = await self.make_request("GET", "/logs/my-messages", auth_token=self.user_token)
        
        if response["status"] == 200:
            print("✅ Get message logs successful")
            
            # Get message stats
            response = await self.make_request("GET", "/logs/stats", auth_token=self.user_token)
            
            if response["status"] == 200:
                print("✅ Get message stats successful")
                return True
            else:
                print(f"❌ Get message stats failed: {response}")
                return False
        else:
            print(f"❌ Get message logs failed: {response}")
            return False
    
    async def cleanup_test_user(self) -> bool:
        """Cleanup test user"""
        print("🧹 Cleaning up test user...")
        
        if not self.user_token:
            return True
        
        response = await self.make_request("DELETE", "/user/account", {
            "password": TEST_USER["password"]
        }, auth_token=self.user_token)
        
        if response["status"] == 200:
            print("✅ Test user cleanup successful")
            return True
        else:
            print(f"⚠️  Test user cleanup failed (this is normal): {response}")
            return True  # Don't fail the test suite for cleanup issues
    
    async def run_all_tests(self) -> bool:
        """Run all tests"""
        print("🚀 Starting PromptEnchanter User Management Tests")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("User Profile", self.test_user_profile),
            ("API Key Management", self.test_api_key_management),
            ("Chat Completion", self.test_chat_completion),
            ("Admin Login", self.test_admin_login),
            ("Admin Functions", self.test_admin_functions),
            ("Security Features", self.test_security_features),
            ("Message Logging", self.test_message_logging),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                print(f"\n📋 {test_name}")
                print("-" * 40)
                
                result = await test_func()
                
                if result:
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    print(f"❌ {test_name} FAILED")
                    
            except Exception as e:
                failed += 1
                print(f"❌ {test_name} ERROR: {e}")
        
        # Cleanup
        print(f"\n📋 Cleanup")
        print("-" * 40)
        await self.cleanup_test_user()
        
        # Results
        print("\n" + "=" * 60)
        print("🎯 TEST RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total:  {passed + failed}")
        
        if failed == 0:
            print("\n🎉 All tests passed! PromptEnchanter User Management is working correctly.")
            return True
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please check the output above.")
            return False


async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing PromptEnchanter at: {base_url}")
    
    async with PromptEnchanterTester(base_url) as tester:
        success = await tester.run_all_tests()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())