"""
Chat completion endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from typing import Optional
import time
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse
from app.services.prompt_service import prompt_service
from app.api.v1.deps.common import get_secure_request_logger
from app.utils.logger import RequestLogger
from app.api.middleware.user_auth import authenticate_api_request
from app.services.message_logging_service import message_logging_service

router = APIRouter()


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
    - User authentication and rate limiting
    - Message logging and analytics
    
    The request is enhanced and forwarded to the configured AI API (WAPI).
    
    **Authentication Required**: Bearer token with valid API key
    """
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None),
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Create enhanced chat completion with user authentication"""
    
    start_time = time.time()
    
    try:
        # Authenticate user
        success, user_data, error_message = await authenticate_api_request(http_request)
        if not success:
            status_code = 429 if "limit exceeded" in error_message.lower() else 401
            raise HTTPException(
                status_code=status_code,
                detail=error_message
            )
        
        # Validate request
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Messages cannot be empty"
            )
        
        # Store request data for logging
        http_request.state.request_data = request.dict()
        
        # Process the request
        response = await prompt_service.process_chat_completion(request, request_logger)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the API request and response
        await message_logging_service.log_message(
            username=user_data['username'],
            email=user_data['email'],
            model=request.level.value,
            messages=[{
                'request': [msg.dict() for msg in request.messages],
                'response': response.dict() if response else None
            }],
            research_model=request.ai_research or False,
            tokens_used=response.usage.total_tokens if response and response.usage else 0,
            processing_time_ms=processing_time_ms
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