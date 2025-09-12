"""
Batch processing endpoints for PromptEnchanter
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import BatchRequest, BatchResponse, ErrorResponse
from app.services.batch_service import batch_service
from app.api.v1.deps.common import get_secure_request_logger
from app.api.middleware.rate_limit import rate_limit
from app.utils.logger import RequestLogger

router = APIRouter()


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
    
    Each prompt in the batch is processed as an individual chat completion
    with the enhancement "Just enhance the prompt with no questions."
    """
)
async def process_batch(
    request: BatchRequest,
    request_logger: RequestLogger = Depends(get_secure_request_logger)
):
    """Process batch of prompts"""
    
    try:
        # Validate request
        if not request.batch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch cannot be empty"
            )
        
        if len(request.batch) > 100:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 100 tasks"
            )
        
        # Process the batch
        response = await batch_service.process_batch(request, request_logger)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )