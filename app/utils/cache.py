"""
Caching utilities for PromptEnchanter
"""
import json
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.config.settings import get_settings
from app.utils.logger import get_logger
from app.utils.security import hash_content

logger = get_logger(__name__)
settings = get_settings()


class CacheManager:
    """Redis-based cache manager with fallback to memory"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, tuple] = {}  # (value, expiry)
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(settings.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using memory cache fallback.")
            self._connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self._connected and self._redis:
                value = await self._redis.get(key)
                if value:
                    return json.loads(value)
            else:
                # Fallback to memory cache
                if key in self._memory_cache:
                    value, expiry = self._memory_cache[key]
                    if datetime.utcnow() < expiry:
                        return value
                    else:
                        del self._memory_cache[key]
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """Set value in cache"""
        try:
            if ttl_seconds is None:
                ttl_seconds = settings.cache_ttl_seconds
            
            if self._connected and self._redis:
                serialized = json.dumps(value, default=str)
                await self._redis.setex(key, ttl_seconds, serialized)
                return True
            else:
                # Fallback to memory cache
                expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds)
                self._memory_cache[key] = (value, expiry)
                
                # Simple cleanup of expired items
                if len(self._memory_cache) > 1000:  # Prevent memory bloat
                    await self._cleanup_memory_cache()
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self._connected and self._redis:
                await self._redis.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def _cleanup_memory_cache(self):
        """Clean up expired items from memory cache"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, expiry) in self._memory_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    def generate_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_parts = [prefix] + [str(arg) for arg in args]
        content = ":".join(key_parts)
        return f"pe:{hash_content(content)[:16]}"


# Global cache instance
cache_manager = CacheManager()


class RequestCache:
    """Cache for API requests"""
    
    @staticmethod
    async def get_response(request_hash: str) -> Optional[Dict]:
        """Get cached response"""
        key = cache_manager.generate_cache_key("response", request_hash)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_response(request_hash: str, response: Dict, ttl: int = None) -> bool:
        """Cache response"""
        key = cache_manager.generate_cache_key("response", request_hash)
        return await cache_manager.set(key, response, ttl)


class ResearchCache:
    """Cache for research results"""
    
    @staticmethod
    async def get_research(query_hash: str) -> Optional[Dict]:
        """Get cached research"""
        key = cache_manager.generate_cache_key("research", query_hash)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_research(query_hash: str, research: Dict, ttl: int = None) -> bool:
        """Cache research results"""
        if ttl is None:
            ttl = settings.research_cache_ttl_seconds
        key = cache_manager.generate_cache_key("research", query_hash)
        return await cache_manager.set(key, research, ttl)
    
    @staticmethod
    async def get_search_results(query_hash: str) -> Optional[list]:
        """Get cached search results"""
        key = cache_manager.generate_cache_key("search", query_hash)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_search_results(query_hash: str, results: list, ttl: int = 3600) -> bool:
        """Cache search results"""
        key = cache_manager.generate_cache_key("search", query_hash)
        return await cache_manager.set(key, results, ttl)