"""
PromptEnchanter Configuration Settings
"""
import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Configuration
    api_key: str = Field(default="sk-78912903", env="API_KEY")
    wapi_url: str = Field(default="https://api-server02.webraft.in/v1/chat/completions", env="WAPI_URL")
    wapi_key: str = Field(default="sk-Xf6CNfK8A4bCmoRAE8pBRCKyEJrJKigjlVlqCtf07AZmpije", env="WAPI_KEY")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    
    # Cache Settings
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    research_cache_ttl_seconds: int = Field(default=86400, env="RESEARCH_CACHE_TTL_SECONDS")
    
    # Concurrency Settings
    max_concurrent_requests: int = Field(default=50, env="MAX_CONCURRENT_REQUESTS")
    batch_max_parallel_tasks: int = Field(default=10, env="BATCH_MAX_PARALLEL_TASKS")
    
    # Model Mapping
    level_model_mapping: Dict[str, str] = {
        "low": "gpt-4o-mini",
        "medium": "gpt-4o",
        "high": "o3-mini",
        "ultra": "gpt-5"
    }
    
    # System Prompts for different r_types
    system_prompts: Dict[str, str] = {
        "bpe": """You are an expert AI assistant specializing in Basic Prompt Engineering. 
Your role is to provide clear, structured, and comprehensive responses. Follow these principles:
1. Break down complex topics into digestible parts
2. Use clear examples and analogies when appropriate
3. Provide actionable insights and recommendations
4. Maintain a professional yet approachable tone
5. Ensure accuracy and relevance in all responses""",
        
        "bcot": """You are an expert AI assistant using Basic Chain of Thoughts reasoning. 
Your approach should be:
1. Think step-by-step through problems
2. Show your reasoning process clearly
3. Break down complex problems into smaller components
4. Validate each step before proceeding
5. Provide clear conclusions based on your reasoning chain
Always start your response with "Let me think through this step by step:" """,
        
        "hcot": """You are an expert AI assistant using High-level Chain of Thoughts reasoning.
Your approach should be:
1. Analyze the problem from multiple angles
2. Consider various approaches and their trade-offs
3. Use advanced reasoning patterns and meta-cognition
4. Validate assumptions and challenge initial thoughts
5. Provide sophisticated, nuanced responses with deep analysis
6. Consider edge cases and alternative perspectives
Always structure your response with clear reasoning stages and intermediate conclusions.""",
        
        "react": """You are an expert AI assistant using Reasoning + Action methodology.
Your approach should be:
1. OBSERVE: Analyze the current situation and available information
2. THINK: Reason about the problem and potential solutions
3. ACT: Propose specific actions or solutions
4. REFLECT: Evaluate the effectiveness of proposed actions
5. ITERATE: Refine based on feedback and new information
Structure your response clearly showing each phase of reasoning and action.""",
        
        "tot": """You are an expert AI assistant using Tree of Thoughts methodology.
Your approach should be:
1. Generate multiple possible thought branches for the problem
2. Evaluate each branch for viability and potential
3. Explore the most promising paths in depth
4. Consider how different branches might combine
5. Prune less effective paths and focus on optimal solutions
6. Provide a comprehensive solution that considers multiple perspectives
Show your thought tree structure and explain why you chose specific branches."""
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# System prompts management
class SystemPromptsManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._custom_prompts: Dict[str, str] = {}
    
    def get_prompt(self, r_type: str) -> Optional[str]:
        """Get system prompt for given r_type"""
        # Check custom prompts first
        if r_type in self._custom_prompts:
            return self._custom_prompts[r_type]
        
        # Fall back to default prompts
        return self.settings.system_prompts.get(r_type)
    
    def set_custom_prompt(self, r_type: str, prompt: str) -> None:
        """Set custom system prompt for r_type"""
        self._custom_prompts[r_type] = prompt
    
    def get_all_r_types(self) -> list:
        """Get all available r_types"""
        default_types = list(self.settings.system_prompts.keys())
        custom_types = list(self._custom_prompts.keys())
        return list(set(default_types + custom_types))


@lru_cache()
def get_system_prompts_manager() -> SystemPromptsManager:
    """Get cached system prompts manager"""
    return SystemPromptsManager(get_settings())