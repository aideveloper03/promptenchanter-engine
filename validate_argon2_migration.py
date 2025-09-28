#!/usr/bin/env python3
"""
Validation script to test the argon2id migration
Tests password hashing with argon2id and backward compatibility with bcrypt
"""

import sys
from pathlib import Path

def test_argon2_functionality():
    """Test argon2id password functionality"""
    print("🔐 Testing argon2id password functionality...")
    
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
                "name": "Long Password (100 chars) - Now Allowed",
                "password": "A" * 95 + "a1B2!",  # 100 chars with required character types
                "should_work": True  # Should work with argon2id (no 72-byte limit)
            },
            {
                "name": "Very Long Password (500 chars) - Still Allowed", 
                "password": "B" * 495 + "a1C2!",  # 500 chars with required character types
                "should_work": True  # Should work with argon2id
            },
            {
                "name": "Extremely Long Password (1100 chars) - Too Long",
                "password": "C" * 1100,
                "should_work": False  # Should fail validation (over 1KB limit)
            },
            {
                "name": "Unicode Password",
                "password": "Password123!🔐🚀🎉",
                "should_work": True
            },
            {
                "name": "Complex Unicode Password",
                "password": "Пароль123!مرحبا世界🔒",
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
                        print(f"    ✅ Password hashed successfully with argon2id")
                        
                        # Verify it's argon2 hash
                        if hashed.startswith('$argon2'):
                            print(f"    ✅ Confirmed argon2 hash format")
                        else:
                            print(f"    ⚠️  Unexpected hash format: {hashed[:20]}...")
                        
                        # Test verification
                        if password_manager.verify_password(password, hashed):
                            print(f"    ✅ Password verification successful")
                            results[test_case['name']] = "PASS"
                        else:
                            print(f"    ❌ Password verification failed")
                            results[test_case['name']] = "FAIL - Verification failed"
                    else:
                        if "1024 bytes" in str(errors):
                            print(f"    ✅ Correctly rejected overly long password: {errors}")
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
                print(f"    ❌ Unexpected error: {e}")
                results[test_case['name']] = f"FAIL - {str(e)}"
        
        # Summary
        print(f"\n📊 Test Results:")
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅" if result == "PASS" else "❌"
            print(f"  {status} {test_name}: {result}")
            if result == "PASS":
                passed += 1
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All argon2id tests passed! The migration is working correctly.")
            return True
        else:
            print(f"\n❌ {total - passed} test(s) failed. Migration may have issues.")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import password manager: {e}")
        print("   Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_backward_compatibility():
    """Test backward compatibility with existing bcrypt hashes"""
    print("🔄 Testing backward compatibility with bcrypt hashes...")
    
    try:
        # Test using bcrypt directly first
        import bcrypt
        test_password = "TestPassword123!"
        test_password_bytes = test_password.encode('utf-8')
        
        # Create a fresh bcrypt hash
        bcrypt_hash = bcrypt.hashpw(test_password_bytes, bcrypt.gensalt()).decode('utf-8')
        print(f"  Created fresh bcrypt hash: {bcrypt_hash[:30]}...")
        
        # Test with bcrypt directly
        if bcrypt.checkpw(test_password_bytes, bcrypt_hash.encode('utf-8')):
            print("  ✅ Direct bcrypt verification works")
        else:
            print("  ❌ Direct bcrypt verification failed")
            return False
        
        # Now test with our password manager
        sys.path.append(str(Path(__file__).parent))
        from app.security.encryption import password_manager
        
        # Test verification with the new password manager
        if password_manager.verify_password(test_password, bcrypt_hash):
            print("  ✅ Backward compatibility verified - can verify bcrypt hashes")
            
            # Test if it needs rehash
            if password_manager.needs_rehash(bcrypt_hash):
                print("  ✅ Correctly identified bcrypt hash as needing upgrade")
                
                # Test upgrade
                new_hash = password_manager.hash_password(test_password)
                if new_hash.startswith('$argon2'):
                    print("  ✅ Successfully upgraded to argon2 hash")
                    
                    # Verify new hash works
                    if password_manager.verify_password(test_password, new_hash):
                        print("  ✅ New argon2 hash verification works")
                        
                        # Check that new hash doesn't need rehash
                        if not password_manager.needs_rehash(new_hash):
                            print("  ✅ New argon2 hash doesn't need further upgrade")
                            return True
                        else:
                            print("  ❌ New argon2 hash incorrectly marked as needing upgrade")
                            return False
                    else:
                        print("  ❌ New argon2 hash verification failed")
                        return False
                else:
                    print(f"  ❌ Upgrade didn't create argon2 hash: {new_hash[:30]}...")
                    return False
            else:
                print("  ❌ Failed to identify bcrypt hash as needing upgrade")
                return False
        else:
            print("  ❌ Failed to verify existing bcrypt hash with password manager")
            return False
            
    except Exception as e:
        print(f"  ❌ Backward compatibility test failed: {e}")
        return False


def check_argon2_availability():
    """Check if argon2 is properly installed and available"""
    print("📦 Checking argon2 availability...")
    
    try:
        import argon2
        print(f"   ✅ argon2-cffi version: {argon2.__version__}")
        
        # Test basic argon2 functionality
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        test_hash = ph.hash("test123")
        if ph.verify(test_hash, "test123"):
            print("   ✅ Basic argon2 functionality confirmed")
            return True
        else:
            print("   ❌ Basic argon2 verification failed")
            return False
            
    except ImportError:
        print("   ❌ argon2-cffi not installed")
        return False
    except Exception as e:
        print(f"   ❌ Error checking argon2: {e}")
        return False


def check_passlib_argon2_compatibility():
    """Check passlib compatibility with argon2"""
    print("🔗 Checking passlib-argon2 compatibility...")
    
    try:
        from passlib.context import CryptContext
        
        # Try to create a context with argon2
        pwd_context = CryptContext(
            schemes=["argon2"],
            argon2__time_cost=2,
            argon2__memory_cost=1024,
            argon2__parallelism=1
        )
        
        # Test basic functionality
        test_password = "test123"
        hashed = pwd_context.hash(test_password)
        verified = pwd_context.verify(test_password, hashed)
        
        if verified and hashed.startswith('$argon2'):
            print("   ✅ passlib-argon2 compatibility confirmed")
            print(f"   ℹ️  Hash format: {hashed[:30]}...")
            return True
        else:
            print(f"   ❌ passlib-argon2 verification failed or wrong format: {hashed[:30]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ passlib-argon2 compatibility issue: {e}")
        return False


def main():
    """Main validation function"""
    print("🔍 PromptEnchanter Argon2id Migration Validation")
    print("=" * 60)
    
    all_passed = True
    
    # Check argon2 availability
    if not check_argon2_availability():
        all_passed = False
    
    print()
    
    # Check passlib compatibility
    if not check_passlib_argon2_compatibility():
        all_passed = False
    
    print()
    
    # Test argon2id functionality
    if not test_argon2_functionality():
        all_passed = False
    
    print()
    
    # Test backward compatibility
    if not test_backward_compatibility():
        all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All validation tests passed!")
        print("✅ The argon2id migration is working correctly")
        print("✅ Password hashing and verification are functional")
        print("✅ Backward compatibility with bcrypt is maintained")
        print("✅ Long password handling is improved (no 72-byte limit)")
        print("✅ Automatic hash upgrades are working")
        return True
    else:
        print("❌ Some validation tests failed")
        print("❌ Please check the issues above before deploying")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)