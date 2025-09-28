#!/usr/bin/env python3
"""
Legacy validation script for bcrypt functionality
NOTE: This system has been migrated to argon2id. Use validate_argon2_migration.py instead.
This script is kept for reference and testing backward compatibility.
"""

import sys
from pathlib import Path

def test_bcrypt_functionality():
    """Test bcrypt functionality with different password scenarios"""
    print("🔐 Testing bcrypt password functionality...")
    
    try:
        # Import the password manager
        sys.path.append(str(Path(__file__).parent))
        from app.security.encryption import password_manager
        
        # Test cases
        test_cases = [
            {
                "name": "Normal Password",
                "password": "SecurePassword123!",
                "should_work": True
            },
            {
                "name": "Short Password",
                "password": "short",
                "should_work": False  # Will fail validation
            },
            {
                "name": "Long Password (70 chars)",
                "password": "A" * 70,
                "should_work": True  # Should work with truncation
            },
            {
                "name": "Very Long Password (100 chars)",
                "password": "B" * 100,
                "should_work": False  # Should fail validation
            },
            {
                "name": "Unicode Password",
                "password": "Password123!🔐",
                "should_work": True
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            print(f"\n  Testing: {test_case['name']}")
            password = test_case['password']
            
            try:
                # Test password strength validation
                is_strong, errors = password_manager.validate_password_strength(password)
                
                if test_case['should_work']:
                    if is_strong:
                        # Test hashing
                        hashed = password_manager.hash_password(password)
                        print(f"    ✅ Password hashed successfully")
                        
                        # Test verification
                        if password_manager.verify_password(password, hashed):
                            print(f"    ✅ Password verification successful")
                            results[test_case['name']] = "PASS"
                        else:
                            print(f"    ❌ Password verification failed")
                            results[test_case['name']] = "FAIL - Verification failed"
                    else:
                        if "72 bytes" in str(errors):
                            print(f"    ✅ Correctly rejected long password: {errors}")
                            results[test_case['name']] = "PASS"
                        else:
                            print(f"    ❌ Password validation failed: {errors}")
                            results[test_case['name']] = "FAIL - Validation failed"
                else:
                    if not is_strong:
                        print(f"    ✅ Correctly rejected weak password: {errors}")
                        results[test_case['name']] = "PASS"
                    else:
                        print(f"    ❌ Should have rejected password but didn't")
                        results[test_case['name']] = "FAIL - Should have been rejected"
                        
            except Exception as e:
                if "72 bytes" in str(e) or "AttributeError" in str(e):
                    print(f"    ❌ bcrypt issue still present: {e}")
                    results[test_case['name']] = "FAIL - bcrypt issue"
                else:
                    print(f"    ❌ Unexpected error: {e}")
                    results[test_case['name']] = f"FAIL - {str(e)}"
        
        # Summary
        print(f"\n📊 Test Results Summary:")
        print("-" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅" if result == "PASS" else "❌"
            print(f"  {status} {test_name}: {result}")
            if result == "PASS":
                passed += 1
        
        print("-" * 50)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All bcrypt tests passed! The fix is working correctly.")
            return True
        else:
            print(f"\n❌ {total - passed} test(s) failed. bcrypt issue may still exist.")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import password manager: {e}")
        print("   Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def check_bcrypt_version():
    """Check installed bcrypt version"""
    print("📦 Checking bcrypt version...")
    
    try:
        import bcrypt
        version = getattr(bcrypt, '__version__', 'Unknown')
        print(f"   Installed bcrypt version: {version}")
        
        # Check if __about__ attribute exists (the source of the original error)
        if hasattr(bcrypt, '__about__'):
            about_version = bcrypt.__about__.__version__
            print(f"   bcrypt.__about__.__version__: {about_version}")
        else:
            print("   bcrypt.__about__ not available (this is expected with newer versions)")
        
        return True
        
    except ImportError:
        print("❌ bcrypt not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking bcrypt: {e}")
        return False


def check_passlib_compatibility():
    """Check passlib compatibility with bcrypt"""
    print("🔗 Checking passlib-bcrypt compatibility...")
    
    try:
        from passlib.context import CryptContext
        
        # Try to create a context (this is where the original error occurred)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Test basic functionality
        test_password = "test123"
        hashed = pwd_context.hash(test_password)
        verified = pwd_context.verify(test_password, hashed)
        
        if verified:
            print("   ✅ passlib-bcrypt compatibility confirmed")
            return True
        else:
            print("   ❌ passlib-bcrypt verification failed")
            return False
            
    except Exception as e:
        print(f"   ❌ passlib-bcrypt compatibility issue: {e}")
        return False


def main():
    """Main validation function"""
    print("🔍 PromptEnchanter bcrypt Fix Validation")
    print("=" * 50)
    
    all_passed = True
    
    # Check bcrypt version
    if not check_bcrypt_version():
        all_passed = False
    
    print()
    
    # Check passlib compatibility
    if not check_passlib_compatibility():
        all_passed = False
    
    print()
    
    # Test bcrypt functionality
    if not test_bcrypt_functionality():
        all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All validation tests passed!")
        print("✅ The bcrypt fix is working correctly")
        print("✅ Password hashing and verification are functional")
        print("✅ Long password handling is working properly")
        return True
    else:
        print("❌ Some validation tests failed")
        print("⚠️  The bcrypt issue may not be fully resolved")
        print("\nRecommended actions:")
        print("  1. Check that bcrypt==4.0.1 is installed")
        print("  2. Verify all dependencies are correctly installed")
        print("  3. Check for any conflicting package versions")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)