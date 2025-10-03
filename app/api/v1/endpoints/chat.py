"""
Chat completion endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse
from app.services.prompt_service import prompt_service
from app.services.message_logging_service import message_logging_service
from app.api.v1.deps.common import get_secure_request_logger
from app.api.middleware.user_auth import authenticate_api_user, user_auth_middleware
from app.api.middleware.comprehensive_auth import get_current_user_api_mongodb
from app.database.database import get_db_session
from app.database.models import User
from app.utils.logger import RequestLogger, get_logger
from app.security.encryption import ip_security_manager
import time

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Create chat completion",
    description="""
    Create a chat completion with PromptEnchanter enhancements.
    
    Features:
    - Prompt engineering styles (r_type)
    - AI-powered research (ai_research)
    - Level-based model selection
    - Caching and optimization
    - User authentication and credit management
    
    The request is enhanced and forwarded to the configured AI API (WAPI).
    
    **Authentication Required**: Bearer token with valid API key
    **Credits Required**: 1 conversation credit per request
    """
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(authenticate_api_user),
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Create enhanced chat completion with user authentication"""
    
    start_time = time.time()
    
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Messages cannot be empty"
            )
        
        # Deduct conversation credit
        credit_deducted = await user_auth_middleware.deduct_conversation_credit(
            session, current_user
        )
        
        if not credit_deducted:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Insufficient conversation credits",
                    "error_code": "CREDITS_EXHAUSTED",
                    "limits": current_user.limits
                }
            )
        
        # Add user context to request logger
        request_logger.bind(
            user_id=current_user.id,
            username=current_user.username,
            api_key_prefix=current_user.api_key[:10] if current_user.api_key else "unknown"
        )
        
        # Process the request
        response = await prompt_service.process_chat_completion(request, request_logger)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the message conversation
        client_ip = ip_security_manager.get_client_ip(http_request)
        
        await message_logging_service.log_message(
            session=session,
            user=current_user,
            model=response.model,
            request_messages=request.messages,
            response_message=response.choices[0].message if response.choices else None,
            research_enabled=request.ai_research or False,
            r_type=request.r_type,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            processing_time_ms=processing_time_ms,
            ip_address=client_ip
        )
        
        logger.info(
            f"Chat completion successful for user {current_user.username}",
            extra={
                "user_id": current_user.id,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "processing_time_ms": processing_time_ms,
                "r_type": request.r_type,
                "research_enabled": request.ai_research
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(f"Chat completion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )