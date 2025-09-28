#!/usr/bin/env python3
"""
Comprehensive test script for support staff system
Tests support staff login, user management, permissions, and all support features
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

class SupportSystemTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.support_session = None
        self.admin_session = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    async def setup_admin_session(self) -> bool:
        """Setup admin session for creating support staff"""
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/admin/login",
                json={"username": "admin", "password": "admin123"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.admin_session = {
                    "token": result.get("session", {}).get("session_token")
                }
                return True
            else:
                self.log("❌ Admin login failed - support staff creation may not work", "WARN")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin setup exception: {e}", "ERROR")
            return False
    
    async def test_support_staff_creation(self) -> Dict[str, Any]:
        """Test support staff creation (requires admin)"""
        self.log("Testing support staff creation...")
        
        if not self.admin_session:
            admin_ok = await self.setup_admin_session()
            if not admin_ok:
                return {"error": "Admin session required for support staff creation"}
        
        # Test support staff creation
        staff_data = {
            "username": "support_test",
            "name": "Test Support Staff",
            "email": "support@example.com",
            "password": "SupportPassword123!",
            "staff_level": "support"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_session['token']}"}
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/support-staff/create",
                headers=headers,
                json=staff_data
            )
            
            if response.status_code == 200:
                self.log("✅ Support staff creation successful")
                return {"success": True, "staff_data": staff_data}
            else:
                self.log(f"❌ Support staff creation failed: {response.status_code}", "ERROR")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"❌ Support staff creation exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_support_staff_authentication(self) -> Dict[str, Any]:
        """Test support staff authentication"""
        self.log("Testing support staff authentication...")
        
        # Try to login with test support staff
        credentials = {
            "username": "support_test",
            "password": "SupportPassword123!"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/support-staff/login",
                json=credentials
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("✅ Support staff login successful")
                
                # Store support session
                self.support_session = {
                    "token": result.get("session", {}).get("session_token"),
                    "staff_data": result.get("staff", {})
                }
                
                return {"success": True, "data": result}
            else:
                self.log(f"❌ Support staff login failed: {response.status_code}", "ERROR")
                self.log("  Note: Support staff may not exist. Creation test may have failed.", "INFO")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"❌ Support staff login exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_support_staff_profile(self) -> Dict[str, Any]:
        """Test support staff profile operations"""
        self.log("Testing support staff profile...")
        
        if not self.support_session or not self.support_session.get("token"):
            self.log("❌ No support session for profile test", "ERROR")
            return {"error": "No support session"}
        
        headers = {"Authorization": f"Bearer {self.support_session['token']}"}
        results = {}
        
        # Test profile retrieval
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/support-staff/profile",
                headers=headers
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                self.log("  ✅ Support staff profile retrieval successful")
                results["get_profile"] = {"success": True, "data": profile_data}
            else:
                self.log(f"  ❌ Support staff profile retrieval failed: {response.status_code}", "ERROR")
                results["get_profile"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Support staff profile retrieval exception: {e}", "ERROR")
            results["get_profile"] = {"success": False, "exception": str(e)}
        
        # Test permissions retrieval
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/support-staff/permissions",
                headers=headers
            )
            
            if response.status_code == 200:
                permissions_data = response.json()
                self.log("  ✅ Support staff permissions retrieval successful")
                results["get_permissions"] = {"success": True, "data": permissions_data}
            else:
                self.log(f"  ❌ Support staff permissions retrieval failed: {response.status_code}", "ERROR")
                results["get_permissions"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Support staff permissions retrieval exception: {e}", "ERROR")
            results["get_permissions"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_support_user_management(self) -> Dict[str, Any]:
        """Test support staff user management capabilities"""
        self.log("Testing support staff user management...")
        
        if not self.support_session or not self.support_session.get("token"):
            self.log("❌ No support session for user management test", "ERROR")
            return {"error": "No support session"}
        
        headers = {"Authorization": f"Bearer {self.support_session['token']}"}
        results = {}
        
        # Test getting users list
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/support-staff/users?page=1&page_size=10",
                headers=headers
            )
            
            if response.status_code == 200:
                users_data = response.json()
                self.log("  ✅ Support staff users list retrieval successful")
                results["get_users"] = {"success": True, "data": users_data}
                
                # If there are users, test getting specific user details
                if users_data.get("users"):
                    user_id = users_data["users"][0]["id"]
                    
                    try:
                        response = await self.client.get(
                            f"{self.base_url}/{API_VERSION}/support-staff/users/{user_id}",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            user_details = response.json()
                            self.log("  ✅ Support staff user details retrieval successful")
                            results["get_user_details"] = {"success": True, "data": user_details}
                        else:
                            self.log(f"  ❌ Support staff user details failed: {response.status_code}", "ERROR")
                            results["get_user_details"] = {"success": False, "error": response.text}
                            
                    except Exception as e:
                        self.log(f"  ❌ Support staff user details exception: {e}", "ERROR")
                        results["get_user_details"] = {"success": False, "exception": str(e)}
                        
            else:
                self.log(f"  ❌ Support staff users list failed: {response.status_code}", "ERROR")
                results["get_users"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Support staff users list exception: {e}", "ERROR")
            results["get_users"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_support_permissions_enforcement(self) -> Dict[str, Any]:
        """Test support staff permissions enforcement"""
        self.log("Testing support staff permissions enforcement...")
        
        if not self.support_session or not self.support_session.get("token"):
            self.log("❌ No support session for permissions test", "ERROR")
            return {"error": "No support session"}
        
        headers = {"Authorization": f"Bearer {self.support_session['token']}"}
        results = {}
        
        # Test accessing admin-only endpoints (should fail)
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/admin/stats",
                headers=headers
            )
            
            if response.status_code == 401 or response.status_code == 403:
                self.log("  ✅ Admin endpoint properly restricted")
                results["admin_restriction"] = {"success": True, "properly_restricted": True}
            else:
                self.log(f"  ❌ Admin endpoint not properly restricted: {response.status_code}", "ERROR")
                results["admin_restriction"] = {"success": False, "not_restricted": True}
                
        except Exception as e:
            self.log(f"  ❌ Admin restriction test exception: {e}", "ERROR")
            results["admin_restriction"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all support system tests"""
        self.log("🚀 Starting comprehensive support system tests")
        
        test_results = {}
        
        # Support staff creation test
        test_results["staff_creation"] = await self.test_support_staff_creation()
        
        # Support staff authentication test
        test_results["authentication"] = await self.test_support_staff_authentication()
        
        # If authentication failed, skip other tests
        if not test_results["authentication"].get("success"):
            self.log("❌ Support staff authentication failed, skipping authenticated tests", "ERROR")
            self.log("💡 Tip: Ensure admin account exists to create support staff", "INFO")
            return test_results
        
        # Support staff profile tests
        test_results["profile_operations"] = await self.test_support_staff_profile()
        
        # Support user management tests
        test_results["user_management"] = await self.test_support_user_management()
        
        # Permissions enforcement tests
        test_results["permissions_enforcement"] = await self.test_support_permissions_enforcement()
        
        # Summary
        self.log("📊 Support System Test Summary:")
        for test_name, result in test_results.items():
            if isinstance(result, bool):
                status = "✅ PASS" if result else "❌ FAIL"
                self.log(f"  {test_name}: {status}")
            elif isinstance(result, dict):
                if "error" in result:
                    self.log(f"  {test_name}: ❌ FAIL - {result['error']}")
                elif result.get("success"):
                    self.log(f"  {test_name}: ✅ PASS")
                else:
                    self.log(f"  {test_name}: ❌ FAIL")
        
        return test_results


async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"Testing PromptEnchanter Support System at: {base_url}")
    
    async with SupportSystemTester(base_url) as tester:
        results = await tester.run_comprehensive_test()
        
        # Save results to file
        with open("support_system_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\n📋 Test results saved to: support_system_test_results.json")
        
        return results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        print("\n🎯 Support system testing completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)