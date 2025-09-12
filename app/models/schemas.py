"""
Pydantic models for PromptEnchanter API
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: MessageRole
    content: str


class RType(str, Enum):
    BPE = "bpe"  # Basic Prompt Engineering
    BCOT = "bcot"  # Basic Chain of Thoughts
    HCOT = "hcot"  # High Chain of Thoughts
    REACT = "react"  # Reasoning + Action
    TOT = "tot"  # Tree of Thoughts


class Level(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class ResearchDepth(str, Enum):
    BASIC = "basic"
    MEDIUM = "medium"
    HIGH = "high"


# Request Models
class ChatCompletionRequest(BaseModel):
    level: Level
    messages: List[Message]
    r_type: Optional[RType] = None
    ai_research: Optional[bool] = False
    research_depth: Optional[ResearchDepth] = ResearchDepth.BASIC
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None


class BatchTask(BaseModel):
    prompt: str
    r_type: Optional[RType] = RType.BPE
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None


class BatchRequest(BaseModel):
    batch: List[BatchTask]
    level: Level
    enable_research: Optional[bool] = False
    research_depth: Optional[ResearchDepth] = ResearchDepth.BASIC
    parallel: Optional[bool] = True


# Response Models
class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None


class BatchTaskResult(BaseModel):
    task_index: int
    success: bool
    response: Optional[ChatCompletionResponse] = None
    error: Optional[str] = None
    processing_time_ms: int
    tokens_used: int


class BatchResponse(BaseModel):
    batch_id: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    results: List[BatchTaskResult]
    total_tokens_used: int
    total_processing_time_ms: int
    created_at: str


# WAPI Models (for forwarding to external API)
class WAPIMessage(BaseModel):
    role: str
    content: str


class WAPIRequest(BaseModel):
    model: str
    messages: List[WAPIMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None


# Research Models
class ResearchTopic(BaseModel):
    topic: str
    importance: float
    subtopics: List[str] = []


class ResearchResult(BaseModel):
    topic: str
    content: str
    sources: List[str] = []
    confidence: float


class ResearchRequest(BaseModel):
    query: str
    depth: ResearchDepth = ResearchDepth.BASIC
    max_topics: int = 5


class ResearchResponse(BaseModel):
    query: str
    results: List[ResearchResult]
    total_sources: int
    processing_time_ms: int


# Admin Models
class SystemPromptUpdate(BaseModel):
    r_type: RType
    prompt: str


class AdminResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Error Models
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Health Check
class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    redis_connected: bool
    wapi_accessible: bool