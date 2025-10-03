"""
Pydantic schemas for user management system
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class UserType(str, Enum):
    PERSONAL = "Personal"
    BUSINESS = "Business"


class StaffLevel(str, Enum):
    NEW = "new"
    SUPPORT = "support"
    ADVANCED = "advanced"


# Registration Schemas
class UserRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars, 1 number)")
    user_type: UserType = Field(default=UserType.PERSONAL, description="Account type")
    about_me: Optional[str] = Field(default="", max_length=1000, description="About me section")
    hobbies: Optional[str] = Field(default="", max_length=500, description="Hobbies")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserRegistrationResponse(BaseModel):
    success: bool
    message: str
    user_id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    email: str
    api_key: str
    verification_required: bool


# Login Schemas
class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class UserInfo(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    name: str
    email: str
    user_type: str
    subscription_plan: str
    is_verified: bool


class SessionInfo(BaseModel):
    session_token: str
    refresh_token: str
    expires_at: str
    refresh_expires_at: str


class UserLoginResponse(BaseModel):
    success: bool
    message: str
    user: UserInfo
    session: SessionInfo


# Session Management
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    success: bool
    session: SessionInfo


# API Key Management
class APIKeyResponse(BaseModel):
    success: bool
    message: str
    api_key: str  # Encrypted


class RegenerateAPIKeyResponse(BaseModel):
    success: bool
    message: str
    api_key: str  # Encrypted


# User Profile Schemas
class UserProfile(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    name: str
    email: str
    about_me: str
    hobbies: str
    user_type: str
    time_created: datetime
    subscription_plan: str
    credits: Dict[str, int]
    limits: Dict[str, int]
    access_rtype: List[str]
    level: str
    additional_notes: str
    is_verified: bool
    last_login: Optional[datetime]
    last_activity: Optional[datetime]


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    about_me: Optional[str] = Field(None, max_length=1000)
    hobbies: Optional[str] = Field(None, max_length=500)


class UpdateEmailRequest(BaseModel):
    new_email: EmailStr = Field(..., description="New email address")
    current_password: str = Field(..., description="Current password for verification")


class ResetPasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., description="Current password for verification")
    reason: Optional[str] = Field(default="", max_length=500, description="Deletion reason")


# Admin Schemas
class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class AdminInfo(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    name: str
    email: str
    is_super_admin: bool
    permissions: List[str]
    last_login: Optional[datetime]


class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    admin: AdminInfo
    session: SessionInfo


class CreateAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_super_admin: bool = Field(default=False)
    permissions: List[str] = Field(default_factory=list)


class UpdateUserRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    about_me: Optional[str] = Field(None, max_length=1000)
    hobbies: Optional[str] = Field(None, max_length=500)
    user_type: Optional[UserType] = None
    subscription_plan: Optional[str] = None
    credits: Optional[Dict[str, int]] = None
    limits: Optional[Dict[str, int]] = None
    access_rtype: Optional[List[str]] = None
    level: Optional[str] = None
    additional_notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserListResponse(BaseModel):
    users: List[UserProfile]
    total_count: int
    page: int
    page_size: int


# Support Staff Schemas
class CreateSupportStaffRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    staff_level: StaffLevel = Field(default=StaffLevel.NEW)


class SupportStaffInfo(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    name: str
    email: str
    staff_level: str
    is_active: bool
    time_created: datetime
    created_by: str
    last_login: Optional[datetime]


class SupportStaffLoginRequest(BaseModel):
    username: str = Field(..., description="Staff username")
    password: str = Field(..., description="Staff password")


class SupportStaffLoginResponse(BaseModel):
    success: bool
    message: str
    staff: SupportStaffInfo
    session: SessionInfo


# Message Logging Schemas
class MessageLogEntry(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    username: str
    email: str
    model: str
    messages: Dict[str, Any]
    research_enabled: bool
    r_type: Optional[str]
    tokens_used: int
    processing_time_ms: int
    ip_address: Optional[str]
    timestamp: datetime


class MessageLogResponse(BaseModel):
    logs: List[MessageLogEntry]
    total_count: int
    page: int
    page_size: int


# Security Schemas
class SecurityLogEntry(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    event_type: str
    user_id: Optional[str]  # Changed from int to str for MongoDB ObjectId compatibility
    username: Optional[str]
    ip_address: Optional[str]
    details: Optional[Dict[str, Any]]
    severity: str
    timestamp: datetime


class SecurityLogResponse(BaseModel):
    logs: List[SecurityLogEntry]
    total_count: int
    page: int
    page_size: int


class IPWhitelistEntry(BaseModel):
    id: str  # Changed from int to str for MongoDB ObjectId compatibility
    ip_address: str
    ip_range: Optional[str]
    description: str
    is_active: bool
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime]


class AddIPWhitelistRequest(BaseModel):
    ip_address: str = Field(..., description="IP address to whitelist")
    ip_range: Optional[str] = Field(None, description="IP range in CIDR notation")
    description: str = Field(default="", max_length=500)
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class IPWhitelistResponse(BaseModel):
    entries: List[IPWhitelistEntry]
    total_count: int


# Statistics and Monitoring
class UserStatistics(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    users_by_type: Dict[str, int]
    users_by_plan: Dict[str, int]
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


class APIUsageStatistics(BaseModel):
    total_requests: int
    requests_today: int
    requests_this_week: int
    requests_this_month: int
    top_users: List[Dict[str, Any]]
    requests_by_endpoint: Dict[str, int]
    average_response_time: float
    error_rate: float


class SystemHealth(BaseModel):
    status: str
    database_connected: bool
    redis_connected: bool
    total_users: int
    active_sessions: int
    system_load: Dict[str, float]
    uptime_seconds: float


# Error Response Schema
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None


# Generic Success Response
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None