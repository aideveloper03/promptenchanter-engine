"""
API Usage Tracking and Credit Management Middleware for PromptEnchanter
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.database.mongodb import get_mongodb_collection, MongoDBUtils
from app.services.mongodb_user_service import mongodb_user_service
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class APIUsageMiddleware:
    """Middleware for tracking API usage and managing user credits"""
    
    def __init__(self):
        self.usage_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    async def check_user_credits(self, user: Dict[str, Any], endpoint: str, estimated_cost: int = 1) -> bool:
        """Check if user has sufficient credits for the request"""
        
        try:
            # Get user's current credits and limits
            credits = user.get("credits", {"main": 0, "reset": 0})
            limits = user.get("limits", {"conversation_limit": 0, "reset": 0})
            
            main_credits = credits.get("main", 0)
            conversation_limit = limits.get("conversation_limit", 0)
            
            # Check if user has sufficient credits
            if main_credits < estimated_cost:
                logger.warning(f"Insufficient credits for user {user['username']}: {main_credits} < {estimated_cost}")
                return False
            
            # Check conversation limits for chat endpoints
            if "/chat" in endpoint or "/v1/chat" in endpoint:
                if conversation_limit <= 0:
                    logger.warning(f"Conversation limit exceeded for user {user['username']}: {conversation_limit}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user credits: {e}")
            return False
    
    async def deduct_user_credits(self, user_id: str, endpoint: str, cost: int = 1, tokens_used: int = 0) -> bool:
        """Deduct credits from user account"""
        
        try:
            users_collection = await get_mongodb_collection('users')
            
            # Prepare update operations
            update_ops = {
                "$inc": {
                    "credits.main": -cost,
                    "usage_stats.total_requests": 1,
                    "usage_stats.total_tokens": tokens_used
                },
                "$set": {
                    "last_activity": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
            
            # Deduct conversation limit for chat endpoints
            if "/chat" in endpoint or "/v1/chat" in endpoint:
                update_ops["$inc"]["limits.conversation_limit"] = -1
            
            # Update user document
            result = await users_collection.update_one(
                {"_id": user_id},
                update_ops
            )
            
            if result.modified_count > 0:
                logger.info(f"Deducted {cost} credits from user {user_id}")
                return True
            else:
                logger.error(f"Failed to deduct credits from user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deducting user credits: {e}")
            return False
    
    async def log_api_usage(
        self, 
        user_id: str, 
        username: str, 
        api_key: str, 
        endpoint: str, 
        method: str,
        status_code: int,
        processing_time_ms: float,
        tokens_used: int = 0,
        ip_address: str = None,
        user_agent: str = None,
        request_size: int = 0,
        response_size: int = 0,
        error_message: str = None
    ):
        """Log API usage to MongoDB"""
        
        try:
            api_usage_collection = await get_mongodb_collection('api_usage_logs')
            
            usage_doc = {
                "_id": MongoDBUtils.generate_object_id(),
                "user_id": user_id,
                "username": username,
                "api_key_prefix": api_key[:10] if api_key else None,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "processing_time_ms": processing_time_ms,
                "tokens_used": tokens_used,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_size": request_size,
                "response_size": response_size,
                "error_message": error_message,
                "timestamp": datetime.now(),
                "date": datetime.now().date()
            }
            
            # Insert usage log (fire and forget)
            asyncio.create_task(api_usage_collection.insert_one(usage_doc))
            
        except Exception as e:
            logger.error(f"Failed to log API usage: {e}")
    
    async def get_user_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user's API usage statistics"""
        
        try:
            api_usage_collection = await get_mongodb_collection('api_usage_logs')
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Aggregate usage statistics
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": start_date, "$lte": end_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "total_tokens": {"$sum": "$tokens_used"},
                        "total_processing_time": {"$sum": "$processing_time_ms"},
                        "avg_processing_time": {"$avg": "$processing_time_ms"},
                        "success_requests": {
                            "$sum": {"$cond": [{"$lt": ["$status_code", 400]}, 1, 0]}
                        },
                        "error_requests": {
                            "$sum": {"$cond": [{"$gte": ["$status_code", 400]}, 1, 0]}
                        },
                        "endpoints": {"$addToSet": "$endpoint"}
                    }
                }
            ]
            
            result = await api_usage_collection.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                stats.pop("_id", None)
                
                # Calculate success rate
                total_requests = stats.get("total_requests", 0)
                success_requests = stats.get("success_requests", 0)
                stats["success_rate"] = (success_requests / total_requests * 100) if total_requests > 0 else 0
                
                return stats
            else:
                return {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_processing_time": 0,
                    "avg_processing_time": 0,
                    "success_requests": 0,
                    "error_requests": 0,
                    "success_rate": 0,
                    "endpoints": []
                }
                
        except Exception as e:
            logger.error(f"Failed to get user usage stats: {e}")
            return {}
    
    async def check_rate_limits(self, user: Dict[str, Any], endpoint: str) -> bool:
        """Check if user has exceeded rate limits"""
        
        try:
            user_id = str(user["_id"])
            now = datetime.now()
            
            # Check cache first
            cache_key = f"{user_id}:{endpoint}"
            if cache_key in self.usage_cache:
                cache_data = self.usage_cache[cache_key]
                if now - cache_data["timestamp"] < timedelta(seconds=self.cache_ttl):
                    return cache_data["allowed"]
            
            # Query recent usage from database
            api_usage_collection = await get_mongodb_collection('api_usage_logs')
            
            # Check requests in the last minute
            minute_ago = now - timedelta(minutes=1)
            recent_requests = await api_usage_collection.count_documents({
                "user_id": user_id,
                "endpoint": endpoint,
                "timestamp": {"$gte": minute_ago}
            })
            
            # Get user's rate limits based on subscription plan
            subscription_plan = user.get("subscription_plan", "free")
            rate_limits = self._get_rate_limits_for_plan(subscription_plan)
            
            endpoint_limit = rate_limits.get(endpoint, rate_limits.get("default", 60))
            allowed = recent_requests < endpoint_limit
            
            # Cache the result
            self.usage_cache[cache_key] = {
                "allowed": allowed,
                "timestamp": now,
                "requests": recent_requests,
                "limit": endpoint_limit
            }
            
            return allowed
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return True  # Allow request on error
    
    def _get_rate_limits_for_plan(self, plan: str) -> Dict[str, int]:
        """Get rate limits based on subscription plan"""
        
        rate_limits = {
            "free": {
                "default": 30,
                "/v1/chat/completions": 10,
                "/v1/batch": 5
            },
            "pro": {
                "default": 100,
                "/v1/chat/completions": 50,
                "/v1/batch": 20
            },
            "enterprise": {
                "default": 500,
                "/v1/chat/completions": 200,
                "/v1/batch": 100
            }
        }
        
        return rate_limits.get(plan, rate_limits["free"])
    
    async def create_usage_error_response(self, error_type: str, details: Dict[str, Any] = None) -> JSONResponse:
        """Create standardized error response for usage-related errors"""
        
        error_responses = {
            "insufficient_credits": {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "content": {
                    "error": {
                        "message": "Insufficient credits to process request",
                        "type": "insufficient_credits",
                        "code": "CREDITS_EXHAUSTED"
                    }
                }
            },
            "rate_limit_exceeded": {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "content": {
                    "error": {
                        "message": "Rate limit exceeded",
                        "type": "rate_limit_exceeded",
                        "code": "RATE_LIMIT_EXCEEDED"
                    }
                }
            },
            "conversation_limit_exceeded": {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "content": {
                    "error": {
                        "message": "Conversation limit exceeded",
                        "type": "conversation_limit_exceeded",
                        "code": "CONVERSATION_LIMIT_EXCEEDED"
                    }
                }
            }
        }
        
        response_config = error_responses.get(error_type, error_responses["insufficient_credits"])
        
        # Add details if provided
        if details:
            response_config["content"]["error"].update(details)
        
        return JSONResponse(
            status_code=response_config["status_code"],
            content=response_config["content"]
        )


# Global middleware instance
api_usage_middleware = APIUsageMiddleware()


async def check_api_usage_and_credits(
    request: Request,
    user: Dict[str, Any],
    estimated_cost: int = 1
) -> Optional[JSONResponse]:
    """
    Check API usage, rate limits, and credits for a user request.
    Returns None if allowed, JSONResponse with error if not allowed.
    """
    
    try:
        endpoint = request.url.path
        
        # Check rate limits first
        if not await api_usage_middleware.check_rate_limits(user, endpoint):
            logger.warning(f"Rate limit exceeded for user {user['username']} on {endpoint}")
            return await api_usage_middleware.create_usage_error_response(
                "rate_limit_exceeded",
                {"endpoint": endpoint, "user": user["username"]}
            )
        
        # Check user credits
        if not await api_usage_middleware.check_user_credits(user, endpoint, estimated_cost):
            credits = user.get("credits", {"main": 0})
            limits = user.get("limits", {"conversation_limit": 0})
            
            if "/chat" in endpoint and limits.get("conversation_limit", 0) <= 0:
                return await api_usage_middleware.create_usage_error_response(
                    "conversation_limit_exceeded",
                    {
                        "current_limit": limits.get("conversation_limit", 0),
                        "endpoint": endpoint
                    }
                )
            else:
                return await api_usage_middleware.create_usage_error_response(
                    "insufficient_credits",
                    {
                        "current_credits": credits.get("main", 0),
                        "required_credits": estimated_cost,
                        "endpoint": endpoint
                    }
                )
        
        return None  # Request is allowed
        
    except Exception as e:
        logger.error(f"Error in API usage check: {e}")
        return None  # Allow request on error


async def deduct_credits_after_request(
    user_id: str,
    endpoint: str,
    cost: int = 1,
    tokens_used: int = 0
) -> bool:
    """
    Deduct credits after successful request processing.
    Should be called after the request is completed.
    """
    
    return await api_usage_middleware.deduct_user_credits(
        user_id, endpoint, cost, tokens_used
    )


async def log_request_usage(
    user: Dict[str, Any],
    request: Request,
    status_code: int,
    processing_time_ms: float,
    tokens_used: int = 0,
    error_message: str = None
):
    """
    Log API request usage.
    Should be called for every API request.
    """
    
    try:
        # Get request details
        api_key = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Estimate request/response sizes
        request_size = len(str(request.url)) + sum(len(k) + len(v) for k, v in request.headers.items())
        response_size = 0  # Would need to be calculated from actual response
        
        await api_usage_middleware.log_api_usage(
            user_id=str(user["_id"]),
            username=user["username"],
            api_key=api_key,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            processing_time_ms=processing_time_ms,
            tokens_used=tokens_used,
            ip_address=ip_address,
            user_agent=user_agent,
            request_size=request_size,
            response_size=response_size,
            error_message=error_message
        )
        
    except Exception as e:
        logger.error(f"Failed to log request usage: {e}")