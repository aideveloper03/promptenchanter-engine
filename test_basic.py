#!/usr/bin/env python3
"""
Basic test script for PromptEnchanter
Run this to verify the installation works correctly.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import get_settings
from app.utils.cache import cache_manager
from app.services.wapi_client import wapi_client
from app.models.schemas import WAPIRequest, WAPIMessage


async def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    
    print("🧪 Testing PromptEnchanter Basic Functionality")
    print("=" * 50)
    
    # Test 1: Configuration loading
    print("1. Testing configuration...")
    try:
        settings = get_settings()
        print(f"   ✅ Configuration loaded successfully")
        print(f"   📊 API Key: {settings.api_key[:10]}...")
        print(f"   🔗 WAPI URL: {settings.wapi_url}")
        print(f"   🏷️  Model mapping: {len(settings.level_model_mapping)} levels")
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return False
    
    # Test 2: Cache manager
    print("\n2. Testing cache manager...")
    try:
        await cache_manager.connect()
        test_key = "test:key"
        test_value = {"test": "data"}
        
        await cache_manager.set(test_key, test_value, 60)
        retrieved = await cache_manager.get(test_key)
        
        if retrieved == test_value:
            print(f"   ✅ Cache working (using {'Redis' if cache_manager._connected else 'Memory'})")
        else:
            print(f"   ⚠️  Cache working but data mismatch")
        
        await cache_manager.delete(test_key)
    except Exception as e:
        print(f"   ⚠️  Cache manager: {e} (will use memory fallback)")
    
    # Test 3: System prompts
    print("\n3. Testing system prompts...")
    try:
        from app.config.settings import get_system_prompts_manager
        prompts_manager = get_system_prompts_manager()
        
        r_types = prompts_manager.get_all_r_types()
        print(f"   ✅ System prompts loaded: {len(r_types)} types")
        for r_type in r_types:
            prompt = prompts_manager.get_prompt(r_type)
            print(f"   📝 {r_type}: {len(prompt)} chars")
    except Exception as e:
        print(f"   ❌ System prompts failed: {e}")
        return False
    
    # Test 4: Model schemas
    print("\n4. Testing model schemas...")
    try:
        from app.models.schemas import ChatCompletionRequest, Message, MessageRole, Level, RType
        
        # Create a test request
        request = ChatCompletionRequest(
            level=Level.MEDIUM,
            messages=[Message(role=MessageRole.USER, content="Test message")],
            r_type=RType.BPE,
            temperature=0.7
        )
        
        print(f"   ✅ Models working: {len(request.messages)} message(s)")
        print(f"   🎛️  Level: {request.level}, R-Type: {request.r_type}")
    except Exception as e:
        print(f"   ❌ Model schemas failed: {e}")
        return False
    
    # Test 5: WAPI client (without actual request)
    print("\n5. Testing WAPI client setup...")
    try:
        # Just test the client initialization
        client = wapi_client
        print(f"   ✅ WAPI client initialized")
        print(f"   🔗 Base URL: {client.base_url}")
        print(f"   🔑 API Key configured: {'Yes' if client.api_key else 'No'}")
    except Exception as e:
        print(f"   ❌ WAPI client failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Basic functionality tests completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Start the server: python main.py")
    print("   2. Visit http://localhost:8000/docs for API documentation")
    print("   3. Test with: curl http://localhost:8000/health")
    
    await cache_manager.disconnect()
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)