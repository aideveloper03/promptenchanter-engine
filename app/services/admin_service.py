"""
Admin Management Service
"""
import json
import secrets
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import logging

from app.database.models import db_manager
from app.security.encryption import security_manager
from app.models.user_schemas import (
    AdminLoginRequest, AdminUserUpdateRequest,
    SupportStaffCreateRequest
)

logger = logging.getLogger(__name__)


class AdminService:
    """Admin management service"""
    
    def __init__(self):
        self.db = db_manager
        self.security = security_manager
        self._ensure_default_admin()
    
    def _ensure_default_admin(self):
        """Ensure default admin exists"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT admin_id FROM admins WHERE username = 'admin' LIMIT 1")
                if not cursor.fetchone():
                    # Create default admin
                    admin_id = f"admin_{secrets.token_urlsafe(8)}"
                    default_password = "Admin123!"  # Change this in production!
                    password_hash = self.security.hash_password(default_password)
                    
                    cursor.execute("""
                        INSERT INTO admins (
                            admin_id, username, name, email, password_hash, 
                            permissions, time_created
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        admin_id, "admin", "System Administrator",
                        "admin@promptenchanter.local", password_hash,
                        "full", datetime.now().isoformat()
                    ))
                    
                    logger.info("Default admin created with username 'admin' and password 'Admin123!'")
                    logger.warning("SECURITY WARNING: Change the default admin password immediately!")
                    
        except Exception as e:
            logger.error(f"Error ensuring default admin: {e}")
    
    async def admin_login(self, request: AdminLoginRequest, ip_address: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Admin login"""
        try:
            # Get admin
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM admins WHERE username = ? AND is_active = 1", (request.username,))
                admin = cursor.fetchone()
                
                if not admin:
                    return False, "Invalid credentials", None
                
                admin = dict(admin)
            
            # Check if admin is locked
            if admin.get('locked_until'):
                locked_until = datetime.fromisoformat(admin['locked_until'])
                if datetime.now() < locked_until:
                    return False, f"Account locked until {locked_until.strftime('%Y-%m-%d %H:%M:%S')}", None
            
            # Verify password
            if not self.security.verify_password(request.password, admin['password_hash']):
                # Increment failed attempts
                failed_attempts = admin.get('failed_login_attempts', 0) + 1
                
                with self.db.get_cursor() as cursor:
                    if failed_attempts >= 3:  # Stricter for admin
                        # Lock account for 2 hours
                        locked_until = (datetime.now() + timedelta(hours=2)).isoformat()
                        cursor.execute(
                            "UPDATE admins SET failed_login_attempts = ?, locked_until = ? WHERE username = ?",
                            (failed_attempts, locked_until, request.username)
                        )
                        return False, "Admin account locked due to failed attempts", None
                    else:
                        cursor.execute(
                            "UPDATE admins SET failed_login_attempts = ? WHERE username = ?",
                            (failed_attempts, request.username)
                        )
                
                return False, "Invalid credentials", None
            
            # Reset failed attempts and update last login
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE admins SET failed_login_attempts = 0, locked_until = '', last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), request.username)
                )
            
            # Create admin session
            session_id = self.db.create_session(
                admin['username'], "admin", ip_address, ""
            )
            
            # Generate JWT token
            token_payload = {
                'username': admin['username'],
                'admin_id': admin['admin_id'],
                'session_id': session_id,
                'user_type': 'admin',
                'permissions': admin['permissions']
            }
            access_token = self.security.generate_jwt_token(token_payload, 8)  # 8 hours
            
            # Prepare admin info
            admin_info = {
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'name': admin['name'],
                'email': admin['email'],
                'permissions': admin['permissions']
            }
            
            return True, "Admin login successful", {
                'access_token': access_token,
                'session_id': session_id,
                'admin_info': admin_info
            }
            
        except Exception as e:
            logger.error(f"Admin login error: {e}")
            return False, "Internal server error", None
    
    async def get_all_users(self, limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Get all users with pagination"""
        try:
            with self.db.get_cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM users")
                total = cursor.fetchone()[0]
                
                # Get users
                cursor.execute("""
                    SELECT username, name, email, user_type, time_created, subscription_plan,
                           level, is_active, email_verified, last_login, credits, limits, access_rtype
                    FROM users 
                    ORDER BY time_created DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                users = []
                for row in cursor.fetchall():
                    user = dict(row)
                    user['credits'] = json.loads(user['credits'])
                    user['limits'] = json.loads(user['limits'])
                    user['access_rtype'] = json.loads(user['access_rtype'])
                    users.append(user)
                
                return users, total
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return [], 0
    
    async def get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """Get detailed user information"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if row:
                    user = dict(row)
                    user['credits'] = json.loads(user['credits'])
                    user['limits'] = json.loads(user['limits'])
                    user['access_rtype'] = json.loads(user['access_rtype'])
                    # Remove password hash for security
                    del user['password_hash']
                    return user
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None
    
    async def update_user(self, username: str, request: AdminUserUpdateRequest) -> Tuple[bool, str]:
        """Update user information (admin only)"""
        try:
            user = self.db.get_user_by_username(username)
            if not user:
                return False, "User not found"
            
            with self.db.get_cursor() as cursor:
                updates = []
                values = []
                
                if request.name is not None:
                    updates.append("name = ?")
                    values.append(request.name)
                
                if request.email is not None:
                    # Check if email already exists
                    cursor.execute("SELECT username FROM users WHERE email = ? AND username != ?", (request.email, username))
                    if cursor.fetchone():
                        return False, "Email already exists"
                    updates.append("email = ?")
                    values.append(request.email)
                
                if request.subscription_plan is not None:
                    updates.append("subscription_plan = ?")
                    values.append(request.subscription_plan.value)
                
                if request.level is not None:
                    updates.append("level = ?")
                    values.append(request.level)
                
                if request.credits is not None:
                    updates.append("credits = ?")
                    values.append(json.dumps(request.credits))
                
                if request.limits is not None:
                    updates.append("limits = ?")
                    values.append(json.dumps(request.limits))
                
                if request.access_rtype is not None:
                    updates.append("access_rtype = ?")
                    values.append(json.dumps(request.access_rtype))
                
                if request.is_active is not None:
                    updates.append("is_active = ?")
                    values.append(request.is_active)
                
                if request.additional_notes is not None:
                    updates.append("additional_notes = ?")
                    values.append(request.additional_notes)
                
                if updates:
                    values.append(username)
                    cursor.execute(
                        f"UPDATE users SET {', '.join(updates)} WHERE username = ?",
                        values
                    )
                    return True, "User updated successfully"
                else:
                    return False, "No fields to update"
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False, "Internal server error"
    
    async def delete_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """Delete user (admin action)"""
        try:
            success = self.db.delete_user(username, f"admin:{admin_username}")
            
            if success:
                return True, "User deleted successfully"
            else:
                return False, "User not found or already deleted"
                
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, "Internal server error"
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            with self.db.get_cursor() as cursor:
                # Total users
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # Active users
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cursor.fetchone()[0]
                
                # Total messages
                cursor.execute("SELECT COUNT(*) FROM message_logs")
                total_messages = cursor.fetchone()[0]
                
                # Messages today
                today = datetime.now().date().isoformat()
                cursor.execute("SELECT COUNT(*) FROM message_logs WHERE date(time) = ?", (today,))
                messages_today = cursor.fetchone()[0]
                
                # API calls today
                cursor.execute("SELECT COUNT(*) FROM api_usage WHERE date(timestamp) = ?", (today,))
                api_calls_today = cursor.fetchone()[0]
                
                # Security stats
                from app.security.firewall import firewall
                firewall_stats = firewall.get_stats()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_messages': total_messages,
                    'messages_today': messages_today,
                    'api_calls_today': api_calls_today,
                    'blocked_ips': firewall_stats['blocked_ips_count'],
                    'security_events_24h': firewall_stats['recent_events_24h'],
                    'firewall_stats': firewall_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    async def get_user_message_logs(self, username: str, limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Get user message logs"""
        try:
            with self.db.get_cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM message_logs WHERE username = ?", (username,))
                total = cursor.fetchone()[0]
                
                # Get logs
                cursor.execute("""
                    SELECT log_id, model, research_model, time, tokens_used, processing_time_ms
                    FROM message_logs 
                    WHERE username = ?
                    ORDER BY time DESC 
                    LIMIT ? OFFSET ?
                """, (username, limit, offset))
                
                logs = [dict(row) for row in cursor.fetchall()]
                return logs, total
                
        except Exception as e:
            logger.error(f"Error getting user message logs: {e}")
            return [], 0
    
    async def create_support_staff(self, request: SupportStaffCreateRequest, admin_username: str) -> Tuple[bool, str, Optional[str]]:
        """Create support staff member"""
        try:
            # Check if username or email already exists
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT staff_id FROM support_staff WHERE username = ? OR email = ?",
                    (request.username, request.email)
                )
                if cursor.fetchone():
                    return False, "Username or email already exists", None
                
                # Hash password
                password_hash = self.security.hash_password(request.password)
                
                # Create staff member
                staff_id = f"staff_{secrets.token_urlsafe(8)}"
                cursor.execute("""
                    INSERT INTO support_staff (
                        staff_id, name, username, email, password_hash, staff_level,
                        time_created, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    staff_id, request.name, request.username, request.email,
                    password_hash, request.staff_level.value,
                    datetime.now().isoformat(), admin_username
                ))
                
                return True, "Support staff created successfully", staff_id
                
        except Exception as e:
            logger.error(f"Error creating support staff: {e}")
            return False, "Internal server error", None
    
    async def get_all_support_staff(self) -> List[Dict[str, Any]]:
        """Get all support staff"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT staff_id, name, username, email, staff_level, 
                           time_created, created_by, is_active, last_login
                    FROM support_staff 
                    ORDER BY time_created DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting support staff: {e}")
            return []
    
    async def update_support_staff_status(self, staff_id: str, is_active: bool) -> Tuple[bool, str]:
        """Update support staff active status"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE support_staff SET is_active = ? WHERE staff_id = ?",
                    (is_active, staff_id)
                )
                
                if cursor.rowcount > 0:
                    status = "activated" if is_active else "deactivated"
                    return True, f"Support staff {status} successfully"
                else:
                    return False, "Support staff not found"
                    
        except Exception as e:
            logger.error(f"Error updating support staff status: {e}")
            return False, "Internal server error"


# Global admin service instance
admin_service = AdminService()