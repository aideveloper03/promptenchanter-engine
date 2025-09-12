"""
Batch Processing Service for PromptEnchanter
"""
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any
from app.models.schemas import (
    BatchRequest, BatchResponse, BatchTask, BatchTaskResult,
    ChatCompletionRequest, Message, MessageRole, Level
)
from app.services.prompt_service import prompt_service
from app.utils.logger import get_logger, RequestLogger
from app.utils.security import generate_batch_id
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class BatchService:
    """Service for processing batch requests"""
    
    def __init__(self):
        self.max_parallel_tasks = settings.batch_max_parallel_tasks
    
    async def process_batch(
        self, 
        request: BatchRequest,
        request_logger: RequestLogger
    ) -> BatchResponse:
        """Process batch of prompts"""
        
        batch_id = generate_batch_id()
        start_time = time.time()
        
        request_logger.info(
            "Starting batch processing",
            batch_id=batch_id,
            total_tasks=len(request.batch),
            parallel=request.parallel,
            enable_research=request.enable_research
        )
        
        try:
            if request.parallel:
                results = await self._process_parallel(request, batch_id, request_logger)
            else:
                results = await self._process_sequential(request, batch_id, request_logger)
            
            # Calculate statistics
            successful_tasks = sum(1 for r in results if r.success)
            failed_tasks = len(results) - successful_tasks
            total_tokens = sum(r.tokens_used for r in results)
            total_processing_time = (time.time() - start_time) * 1000
            
            response = BatchResponse(
                batch_id=batch_id,
                total_tasks=len(request.batch),
                successful_tasks=successful_tasks,
                failed_tasks=failed_tasks,
                results=results,
                total_tokens_used=total_tokens,
                total_processing_time_ms=int(total_processing_time),
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            
            request_logger.info(
                "Batch processing completed",
                batch_id=batch_id,
                successful_tasks=successful_tasks,
                failed_tasks=failed_tasks,
                total_tokens=total_tokens,
                processing_time_ms=int(total_processing_time)
            )
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            request_logger.error(
                "Batch processing failed",
                batch_id=batch_id,
                error=str(e),
                processing_time_ms=int(processing_time)
            )
            raise
    
    async def _process_parallel(
        self, 
        request: BatchRequest,
        batch_id: str,
        request_logger: RequestLogger
    ) -> List[BatchTaskResult]:
        """Process tasks in parallel with concurrency control"""
        
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)
        
        async def process_single_task(task_index: int, task: BatchTask) -> BatchTaskResult:
            async with semaphore:
                return await self._process_single_task(
                    task_index, task, request, batch_id, request_logger
                )
        
        # Create tasks for parallel execution
        tasks = [
            process_single_task(i, task) 
            for i, task in enumerate(request.batch)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(BatchTaskResult(
                    task_index=i,
                    success=False,
                    error=str(result),
                    processing_time_ms=0,
                    tokens_used=0
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_sequential(
        self, 
        request: BatchRequest,
        batch_id: str,
        request_logger: RequestLogger
    ) -> List[BatchTaskResult]:
        """Process tasks sequentially"""
        
        results = []
        for i, task in enumerate(request.batch):
            result = await self._process_single_task(
                i, task, request, batch_id, request_logger
            )
            results.append(result)
        
        return results
    
    async def _process_single_task(
        self,
        task_index: int,
        task: BatchTask,
        batch_request: BatchRequest,
        batch_id: str,
        request_logger: RequestLogger
    ) -> BatchTaskResult:
        """Process a single batch task"""
        
        start_time = time.time()
        
        task_logger = RequestLogger(
            f"{batch_id}:task:{task_index}",
            "batch_processing"
        )
        
        try:
            # Convert batch task to chat completion request
            chat_request = self._convert_batch_task_to_chat_request(
                task, batch_request
            )
            
            # Process the request
            response = await prompt_service.process_chat_completion(
                chat_request, task_logger
            )
            
            processing_time = (time.time() - start_time) * 1000
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            task_logger.info(
                "Batch task completed successfully",
                task_index=task_index,
                processing_time_ms=int(processing_time),
                tokens_used=tokens_used
            )
            
            return BatchTaskResult(
                task_index=task_index,
                success=True,
                response=response,
                processing_time_ms=int(processing_time),
                tokens_used=tokens_used
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            task_logger.error(
                "Batch task failed",
                task_index=task_index,
                error=str(e),
                processing_time_ms=int(processing_time)
            )
            
            return BatchTaskResult(
                task_index=task_index,
                success=False,
                error=str(e),
                processing_time_ms=int(processing_time),
                tokens_used=0
            )
    
    def _convert_batch_task_to_chat_request(
        self,
        task: BatchTask,
        batch_request: BatchRequest
    ) -> ChatCompletionRequest:
        """Convert batch task to chat completion request"""
        
        # Enhance the prompt for batch processing
        enhanced_prompt = f"{task.prompt}\n\nJust enhance the prompt with no questions."
        
        # Create messages
        messages = [Message(
            role=MessageRole.USER,
            content=enhanced_prompt
        )]
        
        return ChatCompletionRequest(
            level=batch_request.level,
            messages=messages,
            r_type=task.r_type,
            ai_research=batch_request.enable_research,
            research_depth=batch_request.research_depth,
            temperature=task.temperature,
            max_tokens=task.max_tokens,
            top_p=task.top_p,
            frequency_penalty=task.frequency_penalty,
            presence_penalty=task.presence_penalty,
            stop=task.stop
        )


# Global batch service instance
batch_service = BatchService()