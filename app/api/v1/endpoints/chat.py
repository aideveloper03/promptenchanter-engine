"""
Chat completion endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse
from app.services.prompt_service import prompt_service
from app.api.v1.deps.common import get_secure_request_logger
from app.utils.logger import RequestLogger

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
    
    The request is enhanced and forwarded to the configured AI API (WAPI).
    """
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Create enhanced chat completion"""
    
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Messages cannot be empty"
            )
        
        # Process the request
        response = await prompt_service.process_chat_completion(request, request_logger)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(f"Chat completion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )