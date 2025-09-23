"""
Batch processing endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import BatchRequest, BatchResponse, ErrorResponse
from app.services.batch_service import batch_service
from app.api.v1.deps.common import get_secure_request_logger
from app.api.middleware.rate_limit import rate_limit
from app.api.middleware.user_auth import authenticate_api_user, user_auth_middleware
from app.database.database import get_db_session
from app.database.models import User
from app.utils.logger import RequestLogger, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/process",
    response_model=BatchResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Process batch of prompts",
    description="""
    Process a batch of prompts with PromptEnchanter enhancements.
    
    Features:
    - Parallel or sequential processing
    - Batch-level research enabling
    - Progress tracking and error handling
    - Token usage and timing statistics
    - User authentication and credit management
    
    Each prompt in the batch is processed as an individual chat completion
    with the enhancement "Just enhance the prompt with no questions."
    
    **Authentication Required**: Bearer token with valid API key
    **Credits Required**: 1 conversation credit per task in batch
    """
)
async def process_batch(
    request: BatchRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(authenticate_api_user),
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Process batch of prompts with user authentication"""
    
    try:
        # Validate request
        if not request.batch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch cannot be empty"
            )
        
        if len(request.batch) > 50:  # Reduced limit due to credit requirements
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 50 tasks"
            )
        
        # Check if user has enough credits for the entire batch
        current_limits = current_user.limits or {"conversation_limit": 0, "reset": 0}
        conversation_limit = current_limits.get("conversation_limit", 0)
        
        if conversation_limit < len(request.batch):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Insufficient conversation credits. Need {len(request.batch)}, have {conversation_limit}",
                    "error_code": "CREDITS_EXHAUSTED",
                    "required_credits": len(request.batch),
                    "available_credits": conversation_limit,
                    "limits": current_user.limits
                }
            )
        
        # Deduct credits for the entire batch upfront
        credits_deducted = 0
        for _ in range(len(request.batch)):
            if await user_auth_middleware.deduct_conversation_credit(session, current_user):
                credits_deducted += 1
            else:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": f"Could only deduct {credits_deducted} out of {len(request.batch)} required credits",
                        "error_code": "CREDITS_EXHAUSTED",
                        "limits": current_user.limits
                    }
                )
        
        # Add user context to request logger
        request_logger.bind(
            user_id=current_user.id,
            username=current_user.username,
            api_key_prefix=current_user.api_key[:10] if current_user.api_key else "unknown",
            batch_size=len(request.batch)
        )
        
        # Process the batch
        response = await batch_service.process_batch(request, request_logger, current_user)
        
        logger.info(
            f"Batch processing successful for user {current_user.username}",
            extra={
                "user_id": current_user.id,
                "batch_size": len(request.batch),
                "successful_tasks": response.successful_tasks,
                "failed_tasks": response.failed_tasks,
                "total_tokens": response.total_tokens_used,
                "processing_time_ms": response.total_processing_time_ms
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )