"""
WAPI (External AI API) Client for PromptEnchanter
"""
import asyncio
import time
from typing import Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config.settings import get_settings
from app.models.schemas import WAPIRequest, ChatCompletionResponse
from app.utils.logger import get_logger, RequestLogger
from app.utils.cache import RequestCache
from app.utils.security import hash_content

settings = get_settings()
logger = get_logger(__name__)


class WAPIClient:
    """Client for communicating with external AI API (WAPI)"""
    
    def __init__(self):
        self.base_url = settings.wapi_url
        self.api_key = settings.wapi_key
        self.timeout = httpx.Timeout(120.0, connect=60.0)
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    
    async def _make_request(self, request: WAPIRequest, request_logger: RequestLogger) -> Dict[str, Any]:
        """Make HTTP request to WAPI"""
        async with self._semaphore:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "PromptEnchanter/1.0"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_logger.debug("Sending request to WAPI", url=self.base_url)
                
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=request.dict(exclude_none=True)
                )
                
                request_logger.info(
                    "WAPI response received",
                    status_code=response.status_code,
                    response_time_ms=response.elapsed.total_seconds() * 1000
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    request_logger.error(
                        "WAPI request failed",
                        status_code=response.status_code,
                        error=error_detail
                    )
                    raise httpx.HTTPStatusError(
                        f"WAPI request failed with status {response.status_code}: {error_detail}",
                        request=response.request,
                        response=response
                    )
                
                return response.json()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def chat_completion(
        self, 
        request: WAPIRequest, 
        request_logger: RequestLogger,
        use_cache: bool = True
    ) -> ChatCompletionResponse:
        """Send chat completion request to WAPI with retry logic"""
        
        # Generate cache key
        request_hash = hash_content(request.json())
        
        # Try cache first
        if use_cache:
            cached_response = await RequestCache.get_response(request_hash)
            if cached_response:
                request_logger.info("Response served from cache")
                return ChatCompletionResponse(**cached_response)
        
        start_time = time.time()
        
        try:
            # Make the request
            response_data = await self._make_request(request, request_logger)
            
            # Convert to our response model
            response = ChatCompletionResponse(**response_data)
            
            # Cache the response
            if use_cache:
                await RequestCache.set_response(request_hash, response.dict())
            
            processing_time = (time.time() - start_time) * 1000
            request_logger.info(
                "Chat completion successful",
                processing_time_ms=processing_time,
                model=request.model,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            request_logger.error(
                "Chat completion failed",
                error=str(e),
                processing_time_ms=processing_time,
                model=request.model
            )
            raise
    
    async def health_check(self) -> bool:
        """Check if WAPI is accessible"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                # Try a simple request to check connectivity
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "PromptEnchanter/1.0"
                }
                
                # Use a minimal request for health check
                test_request = WAPIRequest(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=test_request.dict(exclude_none=True)
                )
                
                return response.status_code in [200, 400, 401]  # 400/401 means API is up but request/auth issue
                
        except Exception as e:
            logger.error(f"WAPI health check failed: {e}")
            return False


# Global WAPI client instance
wapi_client = WAPIClient()