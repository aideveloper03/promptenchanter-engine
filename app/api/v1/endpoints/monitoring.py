"""
Monitoring and utility endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import psutil
import time
from datetime import datetime, timedelta

from app.database.database import get_db_session
from app.database.models import User, MessageLog, APIUsageLog, SecurityLog
from app.api.middleware.user_auth import authenticate_api_user_no_credit_check
from app.services.message_logging_service import message_logging_service
from app.services.credit_reset_service import credit_reset_service
from app.utils.cache import cache_manager
from app.utils.logger import get_logger
from app.config.settings import get_settings
from sqlalchemy import select, func

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.get(
    "/health",
    summary="Health check",
    description="Check system health and component status"
)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Comprehensive health check"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "components": {}
    }
    
    # Check database
    try:
        await session.execute(select(1))
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "sqlite",
            "url": settings.database_url.split("///")[-1] if "///" in settings.database_url else "memory"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    redis_healthy = await cache_manager.is_connected()
    health_status["components"]["redis"] = {
        "status": "healthy" if redis_healthy else "unhealthy",
        "url": settings.redis_url
    }
    if not redis_healthy:
        health_status["status"] = "degraded"
    
    # Check message logging service
    queue_status = message_logging_service.get_queue_status()
    health_status["components"]["message_logging"] = {
        "status": "healthy" if queue_status["is_running"] else "unhealthy",
        "queue_size": queue_status["queue_size"],
        "max_queue_size": queue_status["max_queue_size"]
    }
    
    # Check credit reset service
    credit_status = credit_reset_service.get_status()
    health_status["components"]["credit_reset"] = {
        "status": "healthy" if credit_status["is_running"] else "unhealthy",
        "next_reset": credit_status["next_reset_time"]
    }
    
    # System resources
    try:
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    except Exception:
        health_status["system"] = {"status": "unavailable"}
    
    return health_status


@router.get(
    "/metrics",
    summary="System metrics",
    description="Get detailed system metrics and statistics"
)
async def get_metrics(
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(authenticate_api_user_no_credit_check)
):
    """Get system metrics (requires authentication)"""
    
    try:
        # User statistics
        total_users = await session.execute(select(func.count(User.id)))
        active_users = await session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        
        # API usage statistics (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_api_calls = await session.execute(
            select(func.count(APIUsageLog.id)).where(
                APIUsageLog.timestamp >= yesterday
            )
        )
        
        # Message statistics (last 24 hours)
        recent_messages = await session.execute(
            select(func.count(MessageLog.id)).where(
                MessageLog.timestamp >= yesterday
            )
        )
        
        recent_tokens = await session.execute(
            select(func.sum(MessageLog.tokens_used)).where(
                MessageLog.timestamp >= yesterday
            )
        )
        
        # Security events (last 24 hours)
        recent_security_events = await session.execute(
            select(func.count(SecurityLog.id)).where(
                SecurityLog.timestamp >= yesterday
            )
        )
        
        # Queue status
        queue_status = message_logging_service.get_queue_status()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "user_metrics": {
                "total_users": total_users.scalar(),
                "active_users": active_users.scalar()
            },
            "api_metrics": {
                "api_calls_24h": recent_api_calls.scalar(),
                "messages_24h": recent_messages.scalar(),
                "tokens_used_24h": recent_tokens.scalar() or 0
            },
            "security_metrics": {
                "security_events_24h": recent_security_events.scalar()
            },
            "system_metrics": {
                "message_queue_size": queue_status["queue_size"],
                "message_queue_max": queue_status["max_queue_size"],
                "queue_utilization": queue_status["queue_size"] / queue_status["max_queue_size"] * 100
            }
        }
        
        # Add system resources if available
        try:
            metrics["resource_metrics"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "network_io": dict(psutil.net_io_counters()._asdict()) if hasattr(psutil, 'net_io_counters') else None
            }
        except Exception:
            metrics["resource_metrics"] = {"status": "unavailable"}
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve metrics"}
        )


@router.get(
    "/usage",
    summary="User usage statistics",
    description="Get usage statistics for the current user"
)
async def get_user_usage(
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(authenticate_api_user_no_credit_check)
):
    """Get usage statistics for current user"""
    
    try:
        # Message count and tokens (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        message_stats = await session.execute(
            select(
                func.count(MessageLog.id),
                func.sum(MessageLog.tokens_used),
                func.avg(MessageLog.processing_time_ms)
            ).where(
                MessageLog.user_id == current_user.id,
                MessageLog.timestamp >= thirty_days_ago
            )
        )
        
        message_count, total_tokens, avg_processing_time = message_stats.first()
        
        # API usage (last 30 days)
        api_stats = await session.execute(
            select(func.count(APIUsageLog.id)).where(
                APIUsageLog.user_id == current_user.id,
                APIUsageLog.timestamp >= thirty_days_ago
            )
        )
        
        api_calls = api_stats.scalar()
        
        # Usage by r_type
        rtype_stats = await session.execute(
            select(
                MessageLog.r_type,
                func.count(MessageLog.id)
            ).where(
                MessageLog.user_id == current_user.id,
                MessageLog.timestamp >= thirty_days_ago
            ).group_by(MessageLog.r_type)
        )
        
        rtype_usage = {row[0] or "none": row[1] for row in rtype_stats.fetchall()}
        
        # Daily usage (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        daily_stats = await session.execute(
            select(
                func.date(MessageLog.timestamp),
                func.count(MessageLog.id),
                func.sum(MessageLog.tokens_used)
            ).where(
                MessageLog.user_id == current_user.id,
                MessageLog.timestamp >= seven_days_ago
            ).group_by(func.date(MessageLog.timestamp))
        )
        
        daily_usage = [
            {
                "date": str(row[0]),
                "messages": row[1],
                "tokens": row[2] or 0
            }
            for row in daily_stats.fetchall()
        ]
        
        usage_stats = {
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": datetime.now().isoformat(),
            "period": "last_30_days",
            "summary": {
                "total_messages": message_count or 0,
                "total_tokens": total_tokens or 0,
                "total_api_calls": api_calls or 0,
                "avg_processing_time_ms": float(avg_processing_time) if avg_processing_time else 0
            },
            "current_limits": current_user.limits,
            "current_credits": current_user.credits,
            "usage_by_type": rtype_usage,
            "daily_usage": daily_usage
        }
        
        return usage_stats
        
    except Exception as e:
        logger.error(f"Failed to get user usage for {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve usage statistics"}
        )


@router.post(
    "/flush-logs",
    summary="Flush message logs",
    description="Manually trigger message log flush (admin feature)"
)
async def flush_message_logs(
    current_user = Depends(authenticate_api_user_no_credit_check)
):
    """Manually flush message logs"""
    
    # Simple admin check - in production you'd want proper admin authentication
    if not current_user.username.startswith('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin privileges required"}
        )
    
    try:
        # Trigger manual flush
        await message_logging_service._flush_batch()
        
        return {
            "success": True,
            "message": "Message logs flushed successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to flush message logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to flush message logs"}
        )


@router.get(
    "/queue-status",
    summary="Message queue status",
    description="Get current message queue status"
)
async def get_queue_status(
    current_user = Depends(authenticate_api_user_no_credit_check)
):
    """Get message queue status"""
    
    queue_status = message_logging_service.get_queue_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "queue_status": queue_status,
        "utilization_percent": (queue_status["queue_size"] / queue_status["max_queue_size"]) * 100
    }