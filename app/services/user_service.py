"""
User Management Service
"""
import json
import secrets
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import logging
import re
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from app.database.models import db_manager
from app.security.encryption import security_manager, rate_limiter
from app.security.firewall import firewall
from app.models.user_schemas import (
    UserRegistrationRequest, UserLoginRequest, UserProfileUpdateRequest,
    EmailUpdateRequest, PasswordResetRequest, APIKeyRegenerateRequest
)

logger = logging.getLogger(__name__)


class UserService:
    """User management service with security features"""
    
    def __init__(self):
        self.db = db_manager
        self.security = security_manager
        self.rate_limiter = rate_limiter
        self.firewall = firewall
        
        # Email settings (configure as needed)
        self.email_enabled = False  # Disabled by default as requested
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_username = ""
        self.smtp_password = ""
    
    async def register_user(self, request: UserRegistrationRequest, ip_address: str = "") -> Tuple[bool, str, Optional[str]]:
        """Register new user with comprehensive validation"""
        try:
            # Rate limiting check
            if not self.rate_limiter.check_rate_limit(f"register_{ip_address}", max_attempts=5)[0]:
                self.firewall.record_security_event(
                    ip_address, "registration_rate_limit", "medium",
                    "Registration rate limit exceeded"
                )
                return False, "Too many registration attempts. Please try again later.", None
            
            # Validate password strength
            is_strong, strength_message = self.security.validate_password_strength(request.password)
            if not is_strong:
                return False, strength_message, None
            
            # Check if user already exists
            existing_user = self.db.get_user_by_email(request.email)
            if existing_user:
                self.firewall.record_security_event(
                    ip_address, "duplicate_registration", "low",
                    f"Attempted registration with existing email: {request.email}"
                )
                return False, "Email already registered", None
            
            existing_username = self.db.get_user_by_username(request.username)
            if existing_username:
                return False, "Username already taken", None
            
            # Hash password
            password_hash = self.security.hash_password(request.password)
            
            # Prepare user data
            user_data = {
                'username': request.username,
                'name': request.name,
                'email': request.email,
                'password_hash': password_hash,
                'about_me': request.about_me,
                'hobbies': request.hobbies,
                'user_type': request.user_type.value,
                'subscription_plan': 'free',
                'credits': '{"main":5, "reset":5}',
                'limits': '{"conversation_limit":10, "reset":10}',
                'access_rtype': '["bpe","tot"]',
                'level': 'low'
            }
            
            # Create user
            success, result = self.db.create_user(user_data)
            
            if success:
                # Record successful registration
                self.firewall.record_security_event(
                    ip_address, "user_registration", "low",
                    f"User registered: {request.username}"
                )
                
                # Send verification email if enabled
                if self.email_enabled:
                    await self._send_verification_email(request.email, request.name)
                
                return True, "Registration successful", result  # result is the API key
            else:
                return False, f"Registration failed: {result}", None
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, "Internal server error", None
    
    async def login_user(self, request: UserLoginRequest, ip_address: str = "", user_agent: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Login user with security measures"""
        try:
            # Rate limiting check
            rate_check, remaining = self.rate_limiter.check_rate_limit(f"login_{ip_address}", max_attempts=10, window_minutes=15)
            if not rate_check:
                self.firewall.record_security_event(
                    ip_address, "login_rate_limit", "high",
                    f"Login rate limit exceeded for IP: {ip_address}"
                )
                return False, f"Too many login attempts. Please try again later.", None
            
            # Get user
            user = self.db.get_user_by_email(request.email)
            if not user:
                self.rate_limiter.record_attempt(f"login_{ip_address}")
                self.firewall.record_security_event(
                    ip_address, "failed_login", "medium",
                    f"Login attempt with non-existent email: {request.email}"
                )
                return False, "Invalid email or password", None
            
            # Check if user is locked
            if user.get('locked_until'):
                locked_until = datetime.fromisoformat(user['locked_until'])
                if datetime.now() < locked_until:
                    return False, f"Account locked until {locked_until.strftime('%Y-%m-%d %H:%M:%S')}", None
            
            # Verify password
            if not self.security.verify_password(request.password, user['password_hash']):
                # Increment failed attempts
                failed_attempts = user.get('failed_login_attempts', 0) + 1
                
                with self.db.get_cursor() as cursor:
                    if failed_attempts >= 5:
                        # Lock account for 1 hour
                        locked_until = (datetime.now() + timedelta(hours=1)).isoformat()
                        cursor.execute(
                            "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE email = ?",
                            (failed_attempts, locked_until, request.email)
                        )
                        self.firewall.record_security_event(
                            ip_address, "account_locked", "high",
                            f"Account locked due to failed attempts: {request.email}"
                        )
                        return False, "Account locked due to too many failed attempts", None
                    else:
                        cursor.execute(
                            "UPDATE users SET failed_login_attempts = ? WHERE email = ?",
                            (failed_attempts, request.email)
                        )
                
                self.rate_limiter.record_attempt(f"login_{ip_address}")
                self.firewall.record_security_event(
                    ip_address, "failed_login", "medium",
                    f"Failed login attempt for: {request.email}"
                )
                return False, "Invalid email or password", None
            
            # Reset failed attempts on successful login
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET failed_login_attempts = 0, locked_until = '', last_login = ? WHERE email = ?",
                    (datetime.now().isoformat(), request.email)
                )
            
            # Create session
            session_duration = 24 if not request.remember_me else 168  # 24 hours or 7 days
            session_id = self.db.create_session(
                user['username'], "user", ip_address, user_agent
            )
            
            # Generate JWT token
            token_payload = {
                'username': user['username'],
                'email': user['email'],
                'session_id': session_id,
                'user_type': 'user'
            }
            access_token = self.security.generate_jwt_token(token_payload, session_duration)
            
            # Prepare user info (exclude sensitive data)
            user_info = {
                'username': user['username'],
                'name': user['name'],
                'email': user['email'],
                'user_type': user['user_type'],
                'subscription_plan': user['subscription_plan'],
                'level': user['level'],
                'email_verified': bool(user['email_verified'])
            }
            
            # Record successful login
            self.firewall.record_security_event(
                ip_address, "user_login", "low",
                f"Successful login: {user['username']}"
            )
            
            return True, "Login successful", {
                'access_token': access_token,
                'session_id': session_id,
                'user_info': user_info
            }
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, "Internal server error", None
    
    async def authenticate_api_key(self, api_key: str, ip_address: str = "") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Authenticate API key and check limits"""
        try:
            # Rate limiting check
            if not self.rate_limiter.check_rate_limit(f"api_{ip_address}", max_attempts=1000, window_minutes=60)[0]:
                self.firewall.record_security_event(
                    ip_address, "api_rate_limit", "high",
                    "API rate limit exceeded"
                )
                return False, None, "API rate limit exceeded"
            
            # Get user by API key
            user = self.db.get_user_by_key(api_key)
            if not user:
                self.firewall.record_security_event(
                    ip_address, "invalid_api_key", "medium",
                    f"Invalid API key used from IP: {ip_address}"
                )
                return False, None, "Invalid API key"
            
            # Check if user is active
            if not user['is_active']:
                return False, None, "Account deactivated"
            
            # Check conversation limits
            limits = json.loads(user['limits'])
            if limits['conversation_limit'] <= 0:
                return False, None, "Conversation limit exceeded. Limits reset daily."
            
            # Deduct conversation limit
            limits['conversation_limit'] -= 1
            success = self.db.update_user_limits(user['username'], limits)
            
            if not success:
                return False, None, "Failed to update limits"
            
            # Record API usage
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_usage (usage_id, username, endpoint, timestamp, ip_address, success)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    user['username'],
                    'api_authentication',
                    datetime.now().isoformat(),
                    ip_address,
                    True
                ))
            
            return True, user, None
            
        except Exception as e:
            logger.error(f"API authentication error: {e}")
            return False, None, "Authentication error"
    
    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return None
            
            # Remove sensitive information
            profile = {
                'username': user['username'],
                'name': user['name'],
                'email': user['email'],
                'about_me': user['about_me'],
                'hobbies': user['hobbies'],
                'user_type': user['user_type'],
                'time_created': user['time_created'],
                'subscription_plan': user['subscription_plan'],
                'level': user['level'],
                'credits': json.loads(user['credits']),
                'limits': json.loads(user['limits']),
                'access_rtype': json.loads(user['access_rtype']),
                'is_active': bool(user['is_active']),
                'email_verified': bool(user['email_verified'])
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def update_user_profile(self, username: str, request: UserProfileUpdateRequest) -> Tuple[bool, str]:
        """Update user profile"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found"
            
            # Update fields
            with self.db.get_cursor() as cursor:
                updates = []
                values = []
                
                if request.name is not None:
                    updates.append("name = ?")
                    values.append(request.name)
                
                if request.about_me is not None:
                    updates.append("about_me = ?")
                    values.append(request.about_me)
                
                if request.hobbies is not None:
                    updates.append("hobbies = ?")
                    values.append(request.hobbies)
                
                if updates:
                    values.append(username)
                    cursor.execute(
                        f"UPDATE users SET {', '.join(updates)} WHERE username = ?",
                        values
                    )
                    return True, "Profile updated successfully"
                else:
                    return False, "No fields to update"
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False, "Internal server error"
    
    async def regenerate_api_key(self, username: str, current_password: str) -> Tuple[bool, str, Optional[str]]:
        """Regenerate user API key"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found", None
            
            # Verify current password
            if not self.security.verify_password(current_password, user['password_hash']):
                return False, "Invalid password", None
            
            # Generate new API key
            new_api_key = self.db.generate_api_key()
            
            # Update user's API key
            with self.db.get_cursor() as cursor:
                cursor.execute("UPDATE users SET key = ? WHERE username = ?", (new_api_key, username))
            
            return True, "API key regenerated successfully", new_api_key
            
        except Exception as e:
            logger.error(f"Error regenerating API key: {e}")
            return False, "Internal server error", None
    
    async def get_encrypted_api_key(self, username: str) -> Tuple[bool, str, Optional[str]]:
        """Get encrypted API key for secure transmission"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found", None
            
            # Encrypt API key
            encrypted_key = self.security.encrypt_api_key(user['key'])
            key_preview = f"{user['key'][:10]}..."
            
            return True, "API key retrieved", {
                'encrypted_key': encrypted_key,
                'key_preview': key_preview
            }
            
        except Exception as e:
            logger.error(f"Error getting API key: {e}")
            return False, "Internal server error", None
    
    async def change_password(self, username: str, request: PasswordResetRequest) -> Tuple[bool, str]:
        """Change user password"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not self.security.verify_password(request.current_password, user['password_hash']):
                return False, "Invalid current password"
            
            # Validate new password strength
            is_strong, strength_message = self.security.validate_password_strength(request.new_password)
            if not is_strong:
                return False, strength_message
            
            # Hash new password
            new_password_hash = self.security.hash_password(request.new_password)
            
            # Update password
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (new_password_hash, username)
                )
            
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, "Internal server error"
    
    async def delete_user_account(self, username: str, password: str) -> Tuple[bool, str]:
        """Delete user account (move to backup table)"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found"
            
            # Verify password
            if not self.security.verify_password(password, user['password_hash']):
                return False, "Invalid password"
            
            # Delete user (moves to backup table)
            success = self.db.delete_user(username, "user")
            
            if success:
                return True, "Account deleted successfully"
            else:
                return False, "Failed to delete account"
                
        except Exception as e:
            logger.error(f"Error deleting user account: {e}")
            return False, "Internal server error"
    
    async def log_message(self, username: str, email: str, model: str, messages: List[Dict[str, Any]], 
                         research_model: bool = False, tokens_used: int = 0, processing_time_ms: int = 0) -> bool:
        """Log user message"""
        try:
            log_data = {
                'username': username,
                'email': email,
                'model': model,
                'messages': messages,
                'research_model': research_model,
                'tokens_used': tokens_used,
                'processing_time_ms': processing_time_ms
            }
            
            return self.db.log_message(log_data)
            
        except Exception as e:
            logger.error(f"Error logging message: {e}")
            return False
    
    async def _send_verification_email(self, email: str, name: str):
        """Send email verification (if enabled)"""
        if not self.email_enabled:
            return
        
        try:
            # Create verification token
            token = secrets.token_urlsafe(32)
            
            # Email content
            subject = "Verify Your PromptEnchanter Account"
            body = f"""
            Hi {name},
            
            Thank you for registering with PromptEnchanter!
            
            Please click the link below to verify your email address:
            https://your-domain.com/verify-email?token={token}
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            The PromptEnchanter Team
            """
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")


# Global user service instance
user_service = UserService()