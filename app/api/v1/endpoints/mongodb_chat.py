"""
MongoDB-compatible chat completion endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse
from app.services.prompt_service import prompt_service
from app.services.message_logging_service import message_logging_service
from app.api.v1.deps.common import get_secure_request_logger
from app.api.middleware.comprehensive_auth import get_current_user_api_mongodb
from app.database.mongodb import get_mongodb_collection
from app.utils.logger import RequestLogger, get_logger
from app.security.encryption import ip_security_manager
from datetime import datetime
import time

router = APIRouter()
logger = get_logger(__name__)


async def deduct_conversation_credit_mongodb(user: Dict[str, Any]) -> bool:
    """Deduct conversation credit from MongoDB user"""
    try:
        users_collection = await get_mongodb_collection('users')
        
        # Get current limits
        limits = user.get("limits", {"conversation_limit": 0, "reset": 0})
        current_limit = limits.get("conversation_limit", 0)
        
        if current_limit <= 0:
            return False
        
        # Deduct credit
        new_limit = current_limit - 1
        limits["conversation_limit"] = new_limit
        
        # Update user
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "limits": limits,
                "last_activity": datetime.now(),
                "updated_at": datetime.now()
            }}
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to deduct conversation credit: {e}")
        return False


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Create chat completion (MongoDB)",
    description="""
    Create a chat completion with PromptEnchanter enhancements using MongoDB backend.
    
    Features:
    - Prompt engineering styles (r_type)
    - AI-powered research (ai_research)
    - Level-based model selection
    - Caching and optimization
    - User authentication and credit management
    - Email verification enforcement
    
    The request is enhanced and forwarded to the configured AI API (WAPI).
    
    **Authentication Required**: Bearer token with valid API key
    **Credits Required**: 1 conversation credit per request
    **Email Verification**: Required if enabled in settings
    """
)
async def create_chat_completion_mongodb(
    request: ChatCompletionRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user_api_mongodb),
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Create enhanced chat completion with MongoDB user authentication"""
    
    start_time = time.time()
    
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Messages cannot be empty"
            )
        
        # Deduct conversation credit
        credit_deducted = await deduct_conversation_credit_mongodb(current_user)
        
        if not credit_deducted:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Insufficient conversation credits",
                    "error_code": "CREDITS_EXHAUSTED",
                    "limits": current_user.get("limits", {})
                }
            )
        
        # Add user context to request logger
        request_logger.bind(
            user_id=current_user["_id"],
            username=current_user["username"],
            api_key_prefix=current_user["api_key"][:10] if current_user.get("api_key") else "unknown"
        )
        
        # Process the request
        response = await prompt_service.process_chat_completion(request, request_logger)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log message to MongoDB
        try:
            await log_message_mongodb(
                user=current_user,
                request=request,
                response=response,
                processing_time_ms=processing_time_ms,
                ip_address=ip_security_manager.get_client_ip(http_request)
            )
        except Exception as e:
            logger.warning(f"Failed to log message: {e}")
        
        request_logger.info(
            "Chat completion successful",
            processing_time_ms=processing_time_ms,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else 0
        )
        
        return response
        
    except HTTPException:
        # Re-add the credit if processing failed
        try:
            await refund_conversation_credit_mongodb(current_user)
        except Exception as e:
            logger.error(f"Failed to refund credit: {e}")
        raise
        
    except Exception as e:
        # Re-add the credit if processing failed
        try:
            await refund_conversation_credit_mongodb(current_user)
        except Exception as e:
            logger.error(f"Failed to refund credit: {e}")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        request_logger.error(
            "Chat completion failed",
            error=str(e),
            processing_time_ms=processing_time_ms
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during chat completion"
        )


async def refund_conversation_credit_mongodb(user: Dict[str, Any]) -> bool:
    """Refund conversation credit to MongoDB user"""
    try:
        users_collection = await get_mongodb_collection('users')
        
        # Get current limits
        limits = user.get("limits", {"conversation_limit": 0, "reset": 0})
        current_limit = limits.get("conversation_limit", 0)
        
        # Add credit back
        limits["conversation_limit"] = current_limit + 1
        
        # Update user
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "limits": limits,
                "updated_at": datetime.now()
            }}
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to refund conversation credit: {e}")
        return False


async def log_message_mongodb(
    user: Dict[str, Any],
    request: ChatCompletionRequest,
    response: ChatCompletionResponse,
    processing_time_ms: int,
    ip_address: str = None
):
    """Log message to MongoDB"""
    try:
        messages_collection = await get_mongodb_collection('message_logs')
        
        # Prepare message document
        message_doc = {
            "_id": f"{user['_id']}_{int(time.time() * 1000)}",
            "user_id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "model": response.model,
            "messages": {
                "request": request.dict(),
                "response": response.dict()
            },
            "research_enabled": getattr(request, 'ai_research', False),
            "r_type": getattr(request, 'r_type', None),
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "processing_time_ms": processing_time_ms,
            "ip_address": ip_address,
            "timestamp": datetime.now()
        }
        
        await messages_collection.insert_one(message_doc)
        
    except Exception as e:
        logger.error(f"Failed to log message to MongoDB: {e}")
        # Don't raise here as logging failure shouldn't break the main flow