#!/usr/bin/env python3
"""
Comprehensive test script for user management system
Tests registration, login, profile management, and all user features
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "v1"

class UserManagementTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_users = []
        self.test_sessions = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    async def test_health_check(self) -> bool:
        """Test health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.log("✅ Health check passed")
                return True
            else:
                self.log(f"❌ Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Health check error: {e}", "ERROR")
            return False
    
    async def test_user_registration(self) -> Dict[str, Any]:
        """Test user registration with various scenarios"""
        self.log("Testing user registration...")
        
        # Test data for different scenarios
        test_cases = [
            {
                "name": "Valid Registration",
                "data": {
                    "username": "testuser123",
                    "name": "Test User",
                    "email": "testuser@example.com",
                    "password": "SecurePassword123!",
                    "user_type": "Personal",
                    "about_me": "Testing user registration",
                    "hobbies": "Testing, Development"
                },
                "should_succeed": True
            },
            {
                "name": "Duplicate Username",
                "data": {
                    "username": "testuser123",  # Same username
                    "name": "Another User",
                    "email": "different@example.com",
                    "password": "AnotherPassword123!"
                },
                "should_succeed": False
            },
            {
                "name": "Invalid Email",
                "data": {
                    "username": "testuser456",
                    "name": "Test User 2",
                    "email": "invalid-email",
                    "password": "SecurePassword123!"
                },
                "should_succeed": False
            },
            {
                "name": "Weak Password",
                "data": {
                    "username": "testuser789",
                    "name": "Test User 3",
                    "email": "testuser3@example.com",
                    "password": "weak"
                },
                "should_succeed": False
            },
            {
                "name": "Long Password (bcrypt test)",
                "data": {
                    "username": "testuser_long_pwd",
                    "name": "Long Password User",
                    "email": "longpwd@example.com",
                    "password": "A" * 100  # 100 character password to test bcrypt limit
                },
                "should_succeed": False  # Should fail due to length validation
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            try:
                self.log(f"  Testing: {test_case['name']}")
                
                response = await self.client.post(
                    f"{self.base_url}/{API_VERSION}/users/register",
                    json=test_case["data"]
                )
                
                if test_case["should_succeed"]:
                    if response.status_code == 201:
                        result = response.json()
                        self.log(f"    ✅ {test_case['name']}: Registration successful")
                        
                        # Store successful registration for further tests
                        if "testuser123" in test_case["data"]["username"]:
                            self.test_users.append({
                                "username": test_case["data"]["username"],
                                "email": test_case["data"]["email"],
                                "password": test_case["data"]["password"],
                                "user_id": result.get("user_id"),
                                "api_key": result.get("api_key")
                            })
                        
                        results[test_case["name"]] = {"success": True, "data": result}
                    else:
                        self.log(f"    ❌ {test_case['name']}: Expected success but got {response.status_code}", "ERROR")
                        results[test_case["name"]] = {"success": False, "error": response.text}
                else:
                    if response.status_code >= 400:
                        self.log(f"    ✅ {test_case['name']}: Correctly rejected")
                        results[test_case["name"]] = {"success": True, "rejected": True}
                    else:
                        self.log(f"    ❌ {test_case['name']}: Expected failure but got {response.status_code}", "ERROR")
                        results[test_case["name"]] = {"success": False, "unexpected_success": True}
                        
            except Exception as e:
                self.log(f"    ❌ {test_case['name']}: Exception - {e}", "ERROR")
                results[test_case["name"]] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_user_login(self) -> Dict[str, Any]:
        """Test user login with various scenarios"""
        self.log("Testing user login...")
        
        if not self.test_users:
            self.log("❌ No test users available for login test", "ERROR")
            return {"error": "No test users"}
        
        user = self.test_users[0]
        
        # Test valid login
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/users/login",
                json={
                    "email": user["email"],
                    "password": user["password"]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("  ✅ Valid login successful")
                
                # Store session token for further tests
                self.test_sessions[user["username"]] = {
                    "session_token": result["session"]["session_token"],
                    "refresh_token": result["session"]["refresh_token"],
                    "user_data": result["user"]
                }
                
                return {"success": True, "data": result}
            else:
                self.log(f"  ❌ Login failed: {response.status_code}", "ERROR")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Login exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_user_profile_operations(self) -> Dict[str, Any]:
        """Test user profile retrieval and updates"""
        self.log("Testing user profile operations...")
        
        if not self.test_sessions:
            self.log("❌ No active sessions for profile test", "ERROR")
            return {"error": "No active sessions"}
        
        username = list(self.test_sessions.keys())[0]
        session = self.test_sessions[username]
        headers = {"Authorization": f"Bearer {session['session_token']}"}
        
        results = {}
        
        # Test profile retrieval
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/users/profile",
                headers=headers
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                self.log("  ✅ Profile retrieval successful")
                results["get_profile"] = {"success": True, "data": profile_data}
            else:
                self.log(f"  ❌ Profile retrieval failed: {response.status_code}", "ERROR")
                results["get_profile"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Profile retrieval exception: {e}", "ERROR")
            results["get_profile"] = {"success": False, "exception": str(e)}
        
        # Test profile update
        try:
            update_data = {
                "name": "Updated Test User",
                "about_me": "Updated bio after testing",
                "hobbies": "Testing, Development, DevOps"
            }
            
            response = await self.client.put(
                f"{self.base_url}/{API_VERSION}/users/profile",
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 200:
                self.log("  ✅ Profile update successful")
                results["update_profile"] = {"success": True}
            else:
                self.log(f"  ❌ Profile update failed: {response.status_code}", "ERROR")
                results["update_profile"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Profile update exception: {e}", "ERROR")
            results["update_profile"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_api_key_operations(self) -> Dict[str, Any]:
        """Test API key retrieval and regeneration"""
        self.log("Testing API key operations...")
        
        if not self.test_sessions:
            self.log("❌ No active sessions for API key test", "ERROR")
            return {"error": "No active sessions"}
        
        username = list(self.test_sessions.keys())[0]
        session = self.test_sessions[username]
        headers = {"Authorization": f"Bearer {session['session_token']}"}
        
        results = {}
        
        # Test API key retrieval
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/users/api-key",
                headers=headers
            )
            
            if response.status_code == 200:
                api_key_data = response.json()
                self.log("  ✅ API key retrieval successful")
                results["get_api_key"] = {"success": True, "data": api_key_data}
            else:
                self.log(f"  ❌ API key retrieval failed: {response.status_code}", "ERROR")
                results["get_api_key"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ API key retrieval exception: {e}", "ERROR")
            results["get_api_key"] = {"success": False, "exception": str(e)}
        
        # Test API key regeneration
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/users/api-key/regenerate",
                headers=headers
            )
            
            if response.status_code == 200:
                self.log("  ✅ API key regeneration successful")
                results["regenerate_api_key"] = {"success": True}
            else:
                self.log(f"  ❌ API key regeneration failed: {response.status_code}", "ERROR")
                results["regenerate_api_key"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ API key regeneration exception: {e}", "ERROR")
            results["regenerate_api_key"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_session_management(self) -> Dict[str, Any]:
        """Test session refresh and logout"""
        self.log("Testing session management...")
        
        if not self.test_sessions:
            self.log("❌ No active sessions for session test", "ERROR")
            return {"error": "No active sessions"}
        
        username = list(self.test_sessions.keys())[0]
        session = self.test_sessions[username]
        
        results = {}
        
        # Test session refresh
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/users/refresh",
                json={"refresh_token": session["refresh_token"]}
            )
            
            if response.status_code == 200:
                refresh_data = response.json()
                self.log("  ✅ Session refresh successful")
                
                # Update session tokens
                self.test_sessions[username]["session_token"] = refresh_data["session"]["session_token"]
                self.test_sessions[username]["refresh_token"] = refresh_data["session"]["refresh_token"]
                
                results["refresh_session"] = {"success": True, "data": refresh_data}
            else:
                self.log(f"  ❌ Session refresh failed: {response.status_code}", "ERROR")
                results["refresh_session"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Session refresh exception: {e}", "ERROR")
            results["refresh_session"] = {"success": False, "exception": str(e)}
        
        # Test logout (keep this last as it invalidates the session)
        try:
            headers = {"Authorization": f"Bearer {session['session_token']}"}
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/users/logout",
                headers=headers
            )
            
            if response.status_code == 200:
                self.log("  ✅ Logout successful")
                results["logout"] = {"success": True}
            else:
                self.log(f"  ❌ Logout failed: {response.status_code}", "ERROR")
                results["logout"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Logout exception: {e}", "ERROR")
            results["logout"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all user management tests"""
        self.log("🚀 Starting comprehensive user management tests")
        
        test_results = {}
        
        # Health check first
        health_ok = await self.test_health_check()
        test_results["health_check"] = health_ok
        
        if not health_ok:
            self.log("❌ Health check failed, skipping other tests", "ERROR")
            return test_results
        
        # User registration tests
        test_results["registration"] = await self.test_user_registration()
        
        # User login tests
        test_results["login"] = await self.test_user_login()
        
        # Profile operations tests
        test_results["profile_operations"] = await self.test_user_profile_operations()
        
        # API key operations tests
        test_results["api_key_operations"] = await self.test_api_key_operations()
        
        # Session management tests
        test_results["session_management"] = await self.test_session_management()
        
        # Summary
        self.log("📊 Test Summary:")
        for test_name, result in test_results.items():
            if isinstance(result, bool):
                status = "✅ PASS" if result else "❌ FAIL"
                self.log(f"  {test_name}: {status}")
            elif isinstance(result, dict):
                if "error" in result:
                    self.log(f"  {test_name}: ❌ FAIL - {result['error']}")
                else:
                    success_count = sum(1 for v in result.values() if isinstance(v, dict) and v.get("success"))
                    total_count = len(result)
                    self.log(f"  {test_name}: {success_count}/{total_count} tests passed")
        
        return test_results


async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing PromptEnchanter User Management at: {base_url}")
    
    async with UserManagementTester(base_url) as tester:
        results = await tester.run_comprehensive_test()
        
        # Save results to file
        with open("user_management_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\n📋 Test results saved to: user_management_test_results.json")
        
        return results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        print("\n🎯 User management testing completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)