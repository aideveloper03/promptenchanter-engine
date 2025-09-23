"""
Support Staff Service
"""
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import logging

from app.database.models import db_manager
from app.security.encryption import security_manager
from app.models.user_schemas import AdminLoginRequest, AdminUserUpdateRequest

logger = logging.getLogger(__name__)


class SupportService:
    """Support staff service with role-based permissions"""
    
    def __init__(self):
        self.db = db_manager
        self.security = security_manager
    
    async def support_login(self, request: AdminLoginRequest, ip_address: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Support staff login"""
        try:
            # Get support staff
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM support_staff WHERE username = ? AND is_active = 1", (request.username,))
                staff = cursor.fetchone()
                
                if not staff:
                    return False, "Invalid credentials", None
                
                staff = dict(staff)
            
            # Check if staff is locked
            if staff.get('locked_until'):
                locked_until = datetime.fromisoformat(staff['locked_until'])
                if datetime.now() < locked_until:
                    return False, f"Account locked until {locked_until.strftime('%Y-%m-%d %H:%M:%S')}", None
            
            # Verify password
            if not self.security.verify_password(request.password, staff['password_hash']):
                # Increment failed attempts
                failed_attempts = staff.get('failed_login_attempts', 0) + 1
                
                with self.db.get_cursor() as cursor:
                    if failed_attempts >= 5:
                        # Lock account for 1 hour
                        locked_until = (datetime.now() + timedelta(hours=1)).isoformat()
                        cursor.execute(
                            "UPDATE support_staff SET failed_login_attempts = ?, locked_until = ? WHERE username = ?",
                            (failed_attempts, locked_until, request.username)
                        )
                        return False, "Account locked due to failed attempts", None
                    else:
                        cursor.execute(
                            "UPDATE support_staff SET failed_login_attempts = ? WHERE username = ?",
                            (failed_attempts, request.username)
                        )
                
                return False, "Invalid credentials", None
            
            # Reset failed attempts and update last login
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE support_staff SET failed_login_attempts = 0, locked_until = '', last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), request.username)
                )
            
            # Create support session
            session_id = self.db.create_session(
                staff['username'], "support", ip_address, ""
            )
            
            # Generate JWT token
            token_payload = {
                'username': staff['username'],
                'staff_id': staff['staff_id'],
                'session_id': session_id,
                'user_type': 'support',
                'staff_level': staff['staff_level']
            }
            access_token = self.security.generate_jwt_token(token_payload, 8)  # 8 hours
            
            # Prepare staff info
            staff_info = {
                'staff_id': staff['staff_id'],
                'username': staff['username'],
                'name': staff['name'],
                'email': staff['email'],
                'staff_level': staff['staff_level']
            }
            
            return True, "Support login successful", {
                'access_token': access_token,
                'session_id': session_id,
                'staff_info': staff_info
            }
            
        except Exception as e:
            logger.error(f"Support login error: {e}")
            return False, "Internal server error", None
    
    def _check_permission(self, staff_level: str, required_permission: str) -> bool:
        """Check if staff level has required permission"""
        permissions = {
            'new': ['read_user_info'],
            'support': ['read_user_info', 'update_email', 'update_password', 'update_limits', 'update_plan'],
            'advanced': ['read_user_info', 'update_email', 'update_password', 'update_limits', 
                        'update_plan', 'update_profile', 'view_sensitive_data']
        }
        
        return required_permission in permissions.get(staff_level, [])
    
    async def get_user_info(self, username: str, staff_level: str) -> Optional[Dict[str, Any]]:
        """Get user information based on staff level"""
        if not self._check_permission(staff_level, 'read_user_info'):
            return None
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                user = dict(row)
                user['credits'] = json.loads(user['credits'])
                user['limits'] = json.loads(user['limits'])
                user['access_rtype'] = json.loads(user['access_rtype'])
                
                # Filter sensitive data based on staff level
                if staff_level == 'new':
                    # Remove password hash and other sensitive data
                    sensitive_fields = ['password_hash', 'key', 'additional_notes']
                    for field in sensitive_fields:
                        user.pop(field, None)
                elif staff_level == 'support':
                    # Remove password hash but keep other data
                    user.pop('password_hash', None)
                # Advanced level can see all data except password hash
                else:
                    user.pop('password_hash', None)
                
                return user
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def update_user_email(self, username: str, new_email: str, staff_level: str) -> Tuple[bool, str]:
        """Update user email (support level and above)"""
        if not self._check_permission(staff_level, 'update_email'):
            return False, "Insufficient permissions"
        
        try:
            # Check if email already exists
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT username FROM users WHERE email = ? AND username != ?", (new_email, username))
                if cursor.fetchone():
                    return False, "Email already exists"
                
                # Update email
                cursor.execute("UPDATE users SET email = ?, email_verified = 0 WHERE username = ?", (new_email, username))
                
                if cursor.rowcount > 0:
                    return True, "Email updated successfully"
                else:
                    return False, "User not found"
                    
        except Exception as e:
            logger.error(f"Error updating user email: {e}")
            return False, "Internal server error"
    
    async def reset_user_password(self, username: str, new_password: str, staff_level: str) -> Tuple[bool, str]:
        """Reset user password (support level and above)"""
        if not self._check_permission(staff_level, 'update_password'):
            return False, "Insufficient permissions"
        
        try:
            # Validate password strength
            is_strong, strength_message = self.security.validate_password_strength(new_password)
            if not is_strong:
                return False, strength_message
            
            # Hash new password
            password_hash = self.security.hash_password(new_password)
            
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = ?, failed_login_attempts = 0, locked_until = '' WHERE username = ?",
                    (password_hash, username)
                )
                
                if cursor.rowcount > 0:
                    return True, "Password reset successfully"
                else:
                    return False, "User not found"
                    
        except Exception as e:
            logger.error(f"Error resetting user password: {e}")
            return False, "Internal server error"
    
    async def update_user_limits(self, username: str, new_limits: Dict[str, int], staff_level: str) -> Tuple[bool, str]:
        """Update user conversation limits (support level and above)"""
        if not self._check_permission(staff_level, 'update_limits'):
            return False, "Insufficient permissions"
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT limits FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if not row:
                    return False, "User not found"
                
                current_limits = json.loads(row['limits'])
                current_limits.update(new_limits)
                
                cursor.execute(
                    "UPDATE users SET limits = ? WHERE username = ?",
                    (json.dumps(current_limits), username)
                )
                
                return True, "Limits updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating user limits: {e}")
            return False, "Internal server error"
    
    async def update_user_plan(self, username: str, new_plan: str, staff_level: str) -> Tuple[bool, str]:
        """Update user subscription plan (support level and above)"""
        if not self._check_permission(staff_level, 'update_plan'):
            return False, "Insufficient permissions"
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET subscription_plan = ? WHERE username = ?",
                    (new_plan, username)
                )
                
                if cursor.rowcount > 0:
                    return True, "Subscription plan updated successfully"
                else:
                    return False, "User not found"
                    
        except Exception as e:
            logger.error(f"Error updating user plan: {e}")
            return False, "Internal server error"
    
    async def search_users(self, query: str, staff_level: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search users by username or email"""
        if not self._check_permission(staff_level, 'read_user_info'):
            return []
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT username, name, email, user_type, subscription_plan, is_active, email_verified
                    FROM users 
                    WHERE username LIKE ? OR email LIKE ? OR name LIKE ?
                    ORDER BY username
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    async def get_user_activity_summary(self, username: str, staff_level: str) -> Optional[Dict[str, Any]]:
        """Get user activity summary"""
        if not self._check_permission(staff_level, 'read_user_info'):
            return None
        
        try:
            with self.db.get_cursor() as cursor:
                # Get basic user info
                cursor.execute("SELECT last_login, time_created FROM users WHERE username = ?", (username,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    return None
                
                # Get message count
                cursor.execute("SELECT COUNT(*) FROM message_logs WHERE username = ?", (username,))
                message_count = cursor.fetchone()[0]
                
                # Get recent messages (last 7 days)
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM message_logs WHERE username = ? AND time > ?",
                    (username, seven_days_ago)
                )
                recent_messages = cursor.fetchone()[0]
                
                # Get API usage (last 24 hours)
                twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM api_usage WHERE username = ? AND timestamp > ?",
                    (username, twenty_four_hours_ago)
                )
                recent_api_calls = cursor.fetchone()[0]
                
                return {
                    'last_login': user_row['last_login'],
                    'account_created': user_row['time_created'],
                    'total_messages': message_count,
                    'messages_last_7_days': recent_messages,
                    'api_calls_last_24h': recent_api_calls
                }
                
        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return None


# Global support service instance
support_service = SupportService()