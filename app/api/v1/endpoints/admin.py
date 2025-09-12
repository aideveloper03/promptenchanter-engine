"""
Admin endpoints for PromptEnchanter
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import SystemPromptUpdate, AdminResponse, ErrorResponse, HealthResponse
from app.config.settings import get_system_prompts_manager
from app.api.v1.deps.common import get_secure_request_logger
from app.utils.logger import RequestLogger
from app.utils.cache import cache_manager
from app.services.wapi_client import wapi_client
import time

router = APIRouter()
system_prompts_manager = get_system_prompts_manager()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of PromptEnchanter services"
)
async def health_check(
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Health check endpoint"""
    
    start_time = time.time()
    
    try:
        # Check Redis connection
        redis_connected = cache_manager._connected
        if cache_manager._redis:
            try:
                await cache_manager._redis.ping()
                redis_connected = True
            except:
                redis_connected = False
        
        # Check WAPI accessibility
        wapi_accessible = await wapi_client.health_check()
        
        uptime = time.time() - start_time
        
        status_val = "healthy" if redis_connected and wapi_accessible else "degraded"
        
        return HealthResponse(
            status=status_val,
            version="1.0.0",
            uptime_seconds=uptime,
            redis_connected=redis_connected,
            wapi_accessible=wapi_accessible
        )
        
    except Exception as e:
        request_logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@router.get(
    "/system-prompts",
    response_model=AdminResponse,
    summary="Get system prompts",
    description="Get all available system prompts and their r_types"
)
async def get_system_prompts(
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Get all system prompts"""
    
    try:
        r_types = system_prompts_manager.get_all_r_types()
        prompts = {}
        
        for r_type in r_types:
            prompts[r_type] = system_prompts_manager.get_prompt(r_type)
        
        return AdminResponse(
            success=True,
            message="System prompts retrieved successfully",
            data={"prompts": prompts, "r_types": r_types}
        )
        
    except Exception as e:
        request_logger.error(f"Failed to get system prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system prompts"
        )


@router.put(
    "/system-prompts",
    response_model=AdminResponse,
    summary="Update system prompt",
    description="Update or create a custom system prompt for an r_type"
)
async def update_system_prompt(
    update: SystemPromptUpdate,
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Update system prompt"""
    
    try:
        system_prompts_manager.set_custom_prompt(update.r_type, update.prompt)
        
        request_logger.info(f"Updated system prompt for r_type: {update.r_type}")
        
        return AdminResponse(
            success=True,
            message=f"System prompt for '{update.r_type}' updated successfully",
            data={"r_type": update.r_type}
        )
        
    except Exception as e:
        request_logger.error(f"Failed to update system prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system prompt"
        )


@router.delete(
    "/cache",
    response_model=AdminResponse,
    summary="Clear cache",
    description="Clear all cached data (responses and research)"
)
async def clear_cache(
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Clear all cache"""
    
    try:
        # Clear Redis cache if connected
        if cache_manager._connected and cache_manager._redis:
            await cache_manager._redis.flushdb()
        
        # Clear memory cache
        cache_manager._memory_cache.clear()
        
        request_logger.info("Cache cleared successfully")
        
        return AdminResponse(
            success=True,
            message="Cache cleared successfully"
        )
        
    except Exception as e:
        request_logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get(
    "/stats",
    response_model=AdminResponse,
    summary="Get system statistics",
    description="Get system usage statistics and metrics"
)
async def get_stats(
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Get system statistics"""
    
    try:
        stats = {
            "cache": {
                "redis_connected": cache_manager._connected,
                "memory_cache_size": len(cache_manager._memory_cache)
            },
            "wapi": {
                "accessible": await wapi_client.health_check()
            },
            "system": {
                "version": "1.0.0",
                "uptime": time.time()
            }
        }
        
        return AdminResponse(
            success=True,
            message="Statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        request_logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )