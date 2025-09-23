"""
User Management Pydantic Models
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum
from datetime import datetime


class UserType(str, Enum):
    PERSONAL = "Personal"
    BUSINESS = "Business"


class StaffLevel(str, Enum):
    NEW = "new"
    SUPPORT = "support"
    ADVANCED = "advanced"


class SubscriptionPlan(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# Registration Models
class UserRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    confirm_password: str = Field(..., description="Password confirmation")
    about_me: Optional[str] = Field("", max_length=500, description="About me section")
    hobbies: Optional[str] = Field("", max_length=300, description="Hobbies")
    user_type: UserType = Field(UserType.PERSONAL, description="Account type")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserRegistrationResponse(BaseModel):
    success: bool
    message: str
    api_key: Optional[str] = None
    user_id: Optional[str] = None


# Login Models
class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Remember login session")


class UserLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    session_id: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None


# User Profile Models
class UserProfile(BaseModel):
    username: str
    name: str
    email: str
    about_me: str
    hobbies: str
    user_type: UserType
    time_created: str
    subscription_plan: SubscriptionPlan
    level: str
    credits: Dict[str, int]
    limits: Dict[str, int]
    access_rtype: List[str]
    is_active: bool
    email_verified: bool


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    about_me: Optional[str] = Field(None, max_length=500)
    hobbies: Optional[str] = Field(None, max_length=300)


class EmailUpdateRequest(BaseModel):
    new_email: EmailStr = Field(..., description="New email address")
    current_password: str = Field(..., description="Current password for verification")


class PasswordResetRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_new_password: str = Field(..., description="New password confirmation")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


# API Key Models
class APIKeyResponse(BaseModel):
    success: bool
    message: str
    encrypted_key: Optional[str] = None
    key_preview: Optional[str] = None  # First 10 chars + "..."


class APIKeyRegenerateRequest(BaseModel):
    current_password: str = Field(..., description="Current password for verification")


# Admin Models
class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class AdminUserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    level: Optional[str] = None
    credits: Optional[Dict[str, int]] = None
    limits: Optional[Dict[str, int]] = None
    access_rtype: Optional[List[str]] = None
    is_active: Optional[bool] = None
    additional_notes: Optional[str] = None


# Support Staff Models
class SupportStaffCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8)
    staff_level: StaffLevel = Field(StaffLevel.NEW)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()


class SupportStaffProfile(BaseModel):
    staff_id: str
    name: str
    username: str
    email: str
    staff_level: StaffLevel
    time_created: str
    created_by: str
    is_active: bool
    last_login: str


# Message Logging Models
class MessageLogEntry(BaseModel):
    log_id: str
    username: str
    email: str
    model: str
    messages: List[Dict[str, Any]]
    research_model: bool
    time: str
    tokens_used: int
    processing_time_ms: int


class MessageLogQuery(BaseModel):
    username: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    model: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Authentication Models
class AuthenticationResult(BaseModel):
    success: bool
    user_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    remaining_limits: Optional[Dict[str, int]] = None


# System Models
class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_messages: int
    messages_today: int
    api_calls_today: int
    blocked_ips: int
    security_events_24h: int


class SecurityEventModel(BaseModel):
    timestamp: str
    ip_address: str
    event_type: str
    severity: str
    description: str
    user_agent: str
    endpoint: str
    blocked: bool


# Response Models
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    success: bool
    data: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool


# Batch Processing Models
class BatchMessageLog(BaseModel):
    username: str
    email: str
    model: str
    messages: List[Dict[str, Any]]
    research_model: bool
    tokens_used: int
    processing_time_ms: int


class BatchLogRequest(BaseModel):
    logs: List[BatchMessageLog]