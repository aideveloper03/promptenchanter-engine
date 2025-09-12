"""
Core Prompt Enhancement Service for PromptEnchanter
"""
import time
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    ChatCompletionRequest, ChatCompletionResponse, Message, MessageRole,
    WAPIRequest, WAPIMessage, ResearchDepth, RType
)
from app.services.wapi_client import wapi_client
from app.services.research_service import research_service
from app.config.settings import get_settings, get_system_prompts_manager
from app.utils.logger import get_logger, RequestLogger
from app.utils.security import sanitize_input

settings = get_settings()
system_prompts_manager = get_system_prompts_manager()
logger = get_logger(__name__)


class PromptService:
    """Core service for prompt enhancement and processing"""
    
    def __init__(self):
        self.model_mapping = settings.level_model_mapping
    
    async def process_chat_completion(
        self, 
        request: ChatCompletionRequest,
        request_logger: RequestLogger
    ) -> ChatCompletionResponse:
        """Process chat completion request with enhancements"""
        
        start_time = time.time()
        
        request_logger.info(
            "Processing chat completion",
            level=request.level,
            r_type=request.r_type,
            ai_research=request.ai_research,
            message_count=len(request.messages)
        )
        
        try:
            # Step 1: Prepare enhanced messages
            enhanced_messages = await self._enhance_messages(request, request_logger)
            
            # Step 2: Convert to WAPI format
            wapi_request = self._convert_to_wapi_request(request, enhanced_messages)
            
            # Step 3: Send to WAPI
            response = await wapi_client.chat_completion(wapi_request, request_logger)
            
            processing_time = (time.time() - start_time) * 1000
            
            request_logger.info(
                "Chat completion processed successfully",
                processing_time_ms=processing_time,
                model=wapi_request.model,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            request_logger.error(
                "Chat completion processing failed",
                error=str(e),
                processing_time_ms=processing_time
            )
            raise
    
    async def _enhance_messages(
        self, 
        request: ChatCompletionRequest,
        request_logger: RequestLogger
    ) -> List[Message]:
        """Enhance messages with system prompts and research"""
        
        enhanced_messages = []
        
        # Step 1: Add system prompt if r_type is specified
        if request.r_type:
            system_prompt = system_prompts_manager.get_prompt(request.r_type)
            if system_prompt:
                enhanced_messages.append(Message(
                    role=MessageRole.SYSTEM,
                    content=system_prompt
                ))
                request_logger.debug(f"Added system prompt for r_type: {request.r_type}")
        
        # Step 2: Conduct research if requested
        research_content = None
        if request.ai_research and request.messages:
            # Get the user's main query (last user message)
            user_messages = [msg for msg in request.messages if msg.role == MessageRole.USER]
            if user_messages:
                main_query = user_messages[-1].content
                research_content = await self._conduct_research(
                    main_query, 
                    request.research_depth or ResearchDepth.BASIC,
                    request_logger
                )
        
        # Step 3: Process original messages and add research
        for message in request.messages:
            # Skip system messages if we're adding our own
            if message.role == MessageRole.SYSTEM and request.r_type:
                continue
            
            # Enhance user messages with research
            if (message.role == MessageRole.USER and 
                research_content and 
                message == request.messages[-1]):  # Only enhance the last user message
                
                enhanced_content = self._add_research_to_message(message.content, research_content)
                enhanced_messages.append(Message(
                    role=message.role,
                    content=enhanced_content
                ))
                request_logger.info("Added research content to user message")
            else:
                # Sanitize content
                sanitized_content = sanitize_input(message.content, 50000)
                enhanced_messages.append(Message(
                    role=message.role,
                    content=sanitized_content
                ))
        
        return enhanced_messages
    
    async def _conduct_research(
        self, 
        query: str, 
        depth: ResearchDepth,
        request_logger: RequestLogger
    ) -> Optional[str]:
        """Conduct research and return formatted content"""
        
        try:
            research_response = await research_service.conduct_research(
                query=query,
                depth=depth,
                request_logger=request_logger
            )
            
            if research_response.results:
                # Format research content
                formatted_content = "## Research Information\n\n"
                
                for result in research_response.results:
                    formatted_content += f"### {result.topic}\n\n"
                    formatted_content += f"{result.content}\n\n"
                    
                    if result.sources:
                        formatted_content += "**Sources:**\n"
                        for source in result.sources[:3]:  # Limit to 3 sources
                            formatted_content += f"- {source}\n"
                        formatted_content += "\n"
                
                formatted_content += "---\n\n"
                return formatted_content
                
        except Exception as e:
            request_logger.error(f"Research failed: {e}")
        
        return None
    
    def _add_research_to_message(self, original_content: str, research_content: str) -> str:
        """Add research content to user message"""
        
        return f"""{research_content}

## User Query

{original_content}

---

Please use the research information provided above to give a comprehensive and well-informed response to my query."""
    
    def _convert_to_wapi_request(
        self, 
        original_request: ChatCompletionRequest,
        enhanced_messages: List[Message]
    ) -> WAPIRequest:
        """Convert enhanced request to WAPI format"""
        
        # Map level to model
        model = self.model_mapping.get(original_request.level, "gpt-4o-mini")
        
        # Convert messages to WAPI format
        wapi_messages = [
            WAPIMessage(role=msg.role.value, content=msg.content)
            for msg in enhanced_messages
        ]
        
        return WAPIRequest(
            model=model,
            messages=wapi_messages,
            temperature=original_request.temperature,
            max_tokens=original_request.max_tokens,
            top_p=original_request.top_p,
            frequency_penalty=original_request.frequency_penalty,
            presence_penalty=original_request.presence_penalty,
            stop=original_request.stop
        )


# Global prompt service instance
prompt_service = PromptService()