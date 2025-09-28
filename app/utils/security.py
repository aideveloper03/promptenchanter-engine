"""
Security utilities for PromptEnchanter
"""
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config.settings import get_settings

settings = get_settings()
# Use argon2id with backward compatibility for bcrypt
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=1,
    argon2__hash_len=32,
    argon2__salt_len=16
)


def verify_api_key(api_key: str) -> bool:
    """Verify API key against configured key"""
    if not api_key:
        return False
    
    # Remove Bearer prefix if present
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]
    
    return secrets.compare_digest(api_key, settings.api_key)


def generate_request_id() -> str:
    """Generate unique request ID"""
    return secrets.token_urlsafe(16)


def generate_batch_id() -> str:
    """Generate unique batch ID"""
    timestamp = int(datetime.utcnow().timestamp())
    random_part = secrets.token_urlsafe(8)
    return f"batch_{timestamp}_{random_part}"


def hash_content(content: str) -> str:
    """Generate hash for content caching"""
    return hashlib.sha256(content.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially dangerous characters/patterns
    dangerous_patterns = [
        '\x00',  # Null bytes
        '\r\n\r\n',  # HTTP header injection
        '<?php',  # PHP injection
        '<script',  # XSS
        'javascript:',  # JavaScript injection
    ]
    
    for pattern in dangerous_patterns:
        text = text.replace(pattern, '')
    
    return text.strip()


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self._requests = {}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        if key in self._requests:
            self._requests[key] = [
                req_time for req_time in self._requests[key] 
                if req_time > window_start
            ]
        else:
            self._requests[key] = []
        
        # Check if under limit
        if len(self._requests[key]) >= max_requests:
            return False
        
        # Add current request
        self._requests[key].append(now)
        return True