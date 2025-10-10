#!/usr/bin/env python3
"""
Comprehensive test script for admin system
Tests admin login, user management, system monitoring, and all admin features
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

class AdminSystemTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.admin_session = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    async def test_admin_health(self) -> bool:
        """Test admin health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/{API_VERSION}/admin/health")
            if response.status_code == 200:
                self.log("✅ Admin health check passed")
                return True
            else:
                self.log(f"❌ Admin health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Admin health check error: {e}", "ERROR")
            return False
    
    async def test_admin_authentication(self) -> Dict[str, Any]:
        """Test admin authentication"""
        self.log("Testing admin authentication...")
        
        # Note: This requires an admin account to exist
        # In a real deployment, admin accounts should be created via script
        admin_credentials = {
            "username": "admin",
            "password": "admin123"  # Default test admin
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/{API_VERSION}/admin/login",
                json=admin_credentials
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("✅ Admin login successful")
                
                # Store admin session
                self.admin_session = {
                    "token": result.get("session", {}).get("session_token"),
                    "admin_data": result.get("admin", {})
                }
                
                return {"success": True, "data": result}
            else:
                self.log(f"❌ Admin login failed: {response.status_code}", "ERROR")
                self.log("  Note: Admin account may not exist. Run create_admin.py first.", "INFO")
                return {"success": False, "error": response.text, "note": "Admin account may not exist"}
                
        except Exception as e:
            self.log(f"❌ Admin login exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_system_prompts_management(self) -> Dict[str, Any]:
        """Test system prompts management"""
        self.log("Testing system prompts management...")
        
        if not self.admin_session or not self.admin_session.get("token"):
            self.log("❌ No admin session for system prompts test", "ERROR")
            return {"error": "No admin session"}
        
        headers = {"Authorization": f"Bearer {self.admin_session['token']}"}
        results = {}
        
        # Test getting system prompts
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/admin/system-prompts",
                headers=headers
            )
            
            if response.status_code == 200:
                prompts_data = response.json()
                self.log("  ✅ System prompts retrieval successful")
                results["get_prompts"] = {"success": True, "data": prompts_data}
            else:
                self.log(f"  ❌ System prompts retrieval failed: {response.status_code}", "ERROR")
                results["get_prompts"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ System prompts retrieval exception: {e}", "ERROR")
            results["get_prompts"] = {"success": False, "exception": str(e)}
        
        # Test updating a system prompt
        try:
            update_data = {
                "r_type": "test_prompt",
                "prompt": "This is a test system prompt for verification purposes."
            }
            
            response = await self.client.put(
                f"{self.base_url}/{API_VERSION}/admin/system-prompts",
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 200:
                self.log("  ✅ System prompt update successful")
                results["update_prompt"] = {"success": True}
            else:
                self.log(f"  ❌ System prompt update failed: {response.status_code}", "ERROR")
                results["update_prompt"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ System prompt update exception: {e}", "ERROR")
            results["update_prompt"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def test_cache_management(self) -> Dict[str, Any]:
        """Test cache management operations"""
        self.log("Testing cache management...")
        
        if not self.admin_session or not self.admin_session.get("token"):
            self.log("❌ No admin session for cache test", "ERROR")
            return {"error": "No admin session"}
        
        headers = {"Authorization": f"Bearer {self.admin_session['token']}"}
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/{API_VERSION}/admin/cache",
                headers=headers
            )
            
            if response.status_code == 200:
                self.log("  ✅ Cache clear successful")
                return {"success": True}
            else:
                self.log(f"  ❌ Cache clear failed: {response.status_code}", "ERROR")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Cache clear exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_system_statistics(self) -> Dict[str, Any]:
        """Test system statistics retrieval"""
        self.log("Testing system statistics...")
        
        if not self.admin_session or not self.admin_session.get("token"):
            self.log("❌ No admin session for stats test", "ERROR")
            return {"error": "No admin session"}
        
        headers = {"Authorization": f"Bearer {self.admin_session['token']}"}
        
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/admin/stats",
                headers=headers
            )
            
            if response.status_code == 200:
                stats_data = response.json()
                self.log("  ✅ System statistics retrieval successful")
                return {"success": True, "data": stats_data}
            else:
                self.log(f"  ❌ System statistics failed: {response.status_code}", "ERROR")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ System statistics exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    async def test_user_management_admin(self) -> Dict[str, Any]:
        """Test admin user management features"""
        self.log("Testing admin user management...")
        
        if not self.admin_session or not self.admin_session.get("token"):
            self.log("❌ No admin session for user management test", "ERROR")
            return {"error": "No admin session"}
        
        headers = {"Authorization": f"Bearer {self.admin_session['token']}"}
        results = {}
        
        # Test getting users list
        try:
            response = await self.client.get(
                f"{self.base_url}/{API_VERSION}/admin/users?page=1&page_size=10",
                headers=headers
            )
            
            if response.status_code == 200:
                users_data = response.json()
                self.log("  ✅ Users list retrieval successful")
                results["get_users"] = {"success": True, "data": users_data}
            else:
                self.log(f"  ❌ Users list retrieval failed: {response.status_code}", "ERROR")
                results["get_users"] = {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"  ❌ Users list retrieval exception: {e}", "ERROR")
            results["get_users"] = {"success": False, "exception": str(e)}
        
        return results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all admin system tests"""
        self.log("🚀 Starting comprehensive admin system tests")
        
        test_results = {}
        
        # Health check first
        health_ok = await self.test_admin_health()
        test_results["health_check"] = health_ok
        
        if not health_ok:
            self.log("❌ Admin health check failed, skipping authenticated tests", "ERROR")
            return test_results
        
        # Admin authentication test
        test_results["authentication"] = await self.test_admin_authentication()
        
        # If authentication failed, skip other tests
        if not test_results["authentication"].get("success"):
            self.log("❌ Admin authentication failed, skipping authenticated tests", "ERROR")
            self.log("💡 Tip: Create admin account first with: python scripts/create_admin.py", "INFO")
            return test_results
        
        # System prompts management tests
        test_results["system_prompts"] = await self.test_system_prompts_management()
        
        # Cache management tests
        test_results["cache_management"] = await test_cache_management()
        
        # System statistics tests
        test_results["system_statistics"] = await self.test_system_statistics()
        
        # User management tests
        test_results["user_management"] = await self.test_user_management_admin()
        
        # Summary
        self.log("📊 Admin Test Summary:")
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
    
    print(f"Testing PromptEnchanter Admin System at: {base_url}")
    
    async with AdminSystemTester(base_url) as tester:
        results = await tester.run_comprehensive_test()
        
        # Save results to file
        with open("admin_system_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\n📋 Test results saved to: admin_system_test_results.json")
        
        return results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        print("\n🎯 Admin system testing completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)