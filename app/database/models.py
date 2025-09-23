"""
Database models for PromptEnchanter user management system
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """Main user table with all user information"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    about_me = Column(Text, default="")
    hobbies = Column(Text, default="")
    user_type = Column(String(20), default="Personal")  # Personal or Business
    time_created = Column(DateTime, default=func.now(), nullable=False)
    subscription_plan = Column(String(50), default="free")
    credits = Column(JSON, default=lambda: {"main": 5, "reset": 5})
    limits = Column(JSON, default=lambda: {"conversation_limit": 10, "reset": 10})
    access_rtype = Column(JSON, default=lambda: ["bpe", "tot"])
    level = Column(String(20), default="low")
    additional_notes = Column(Text, default="")
    api_key = Column(String(255), unique=True, index=True, nullable=False)
    
    # Security fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Tracking
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime, default=func.now())
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("MessageLog", back_populates="user", cascade="all, delete-orphan")


class DeletedUser(Base):
    """Archive table for deleted users"""
    __tablename__ = "deleted_users"
    
    id = Column(Integer, primary_key=True, index=True)
    original_user_id = Column(Integer, nullable=False)
    username = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    user_type = Column(String(20), nullable=False)
    time_created = Column(DateTime, nullable=False)
    subscription_plan = Column(String(50), nullable=False)
    deletion_reason = Column(Text, default="")
    deleted_at = Column(DateTime, default=func.now())
    deleted_by = Column(String(100), nullable=True)  # admin username or "self"


class UserSession(Base):
    """User session management"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="sessions")


class MessageLog(Base):
    """Message logging for conversations"""
    __tablename__ = "message_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    messages = Column(JSON, nullable=False)  # Full request and response
    research_enabled = Column(Boolean, default=False)
    r_type = Column(String(20), nullable=True)
    tokens_used = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    # Relationship
    user = relationship("User", back_populates="messages")


class Admin(Base):
    """Admin user table"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_super_admin = Column(Boolean, default=False)
    permissions = Column(JSON, default=lambda: [])
    
    # Security fields
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Tracking
    created_at = Column(DateTime, default=func.now())
    created_by = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SupportStaff(Base):
    """Support staff table"""
    __tablename__ = "support_staff"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    staff_level = Column(String(20), default="new")  # new, support, advanced
    
    # Security fields
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Tracking
    time_created = Column(DateTime, default=func.now())
    created_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SecurityLog(Base):
    """Security event logging"""
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(50), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    severity = Column(String(20), default="info")  # info, warning, error, critical
    timestamp = Column(DateTime, default=func.now(), index=True)


class IPWhitelist(Base):
    """IP whitelist for API access"""
    __tablename__ = "ip_whitelist"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    ip_range = Column(String(50), nullable=True)  # CIDR notation
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)


class APIUsageLog(Base):
    """API usage statistics and monitoring"""
    __tablename__ = "api_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    api_key = Column(String(255), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    # Daily aggregation for performance
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD format


class SystemConfig(Base):
    """System configuration storage"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, default="")
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)