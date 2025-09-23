"""
SQLite Database Models for User Management System
"""
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
from contextlib import contextmanager
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User data class"""
    username: str
    name: str
    email: str
    password_hash: str
    about_me: str = ""
    hobbies: str = ""
    user_type: str = "Personal"  # Personal or Business
    time_created: str = ""
    subscription_plan: str = "free"
    credits: str = '{"main":5, "reset":5}'
    limits: str = '{"conversation_limit":10, "reset":10}'
    access_rtype: str = '["bpe","tot"]'
    level: str = "low"
    additional_notes: str = ""
    key: str = ""


@dataclass
class Admin:
    """Admin data class"""
    admin_id: str
    username: str
    name: str
    email: str
    password_hash: str
    permissions: str = "full"
    time_created: str = ""
    last_login: str = ""
    is_active: bool = True


@dataclass
class SupportStaff:
    """Support Staff data class"""
    staff_id: str
    name: str
    username: str
    email: str
    password_hash: str
    staff_level: str = "new"  # new, support, advanced
    time_created: str = ""
    created_by: str = ""
    is_active: bool = True


@dataclass
class MessageLog:
    """Message log data class"""
    log_id: str
    username: str
    email: str
    model: str
    messages: str  # JSON string
    research_model: bool
    time: str
    tokens_used: int = 0
    processing_time_ms: int = 0


class DatabaseManager:
    """Thread-safe SQLite database manager"""
    
    def __init__(self, db_path: str = "user_management.db"):
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._init_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA cache_size=1000")
            self._local.connection.execute("PRAGMA temp_store=memory")
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database tables"""
        with self.get_cursor() as cursor:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    about_me TEXT DEFAULT '',
                    hobbies TEXT DEFAULT '',
                    user_type TEXT DEFAULT 'Personal',
                    time_created TEXT NOT NULL,
                    subscription_plan TEXT DEFAULT 'free',
                    credits TEXT DEFAULT '{"main":5, "reset":5}',
                    limits TEXT DEFAULT '{"conversation_limit":10, "reset":10}',
                    access_rtype TEXT DEFAULT '["bpe","tot"]',
                    level TEXT DEFAULT 'low',
                    additional_notes TEXT DEFAULT '',
                    key TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    email_verified BOOLEAN DEFAULT 0,
                    last_login TEXT DEFAULT '',
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT DEFAULT ''
                )
            """)
            
            # Deleted users backup table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deleted_users (
                    username TEXT,
                    name TEXT,
                    email TEXT,
                    password_hash TEXT,
                    about_me TEXT,
                    hobbies TEXT,
                    user_type TEXT,
                    time_created TEXT,
                    subscription_plan TEXT,
                    credits TEXT,
                    limits TEXT,
                    access_rtype TEXT,
                    level TEXT,
                    additional_notes TEXT,
                    key TEXT,
                    deleted_at TEXT NOT NULL,
                    deleted_by TEXT DEFAULT 'user'
                )
            """)
            
            # Admin table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    admin_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    permissions TEXT DEFAULT 'full',
                    time_created TEXT NOT NULL,
                    last_login TEXT DEFAULT '',
                    is_active BOOLEAN DEFAULT 1,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT DEFAULT ''
                )
            """)
            
            # Support staff table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_staff (
                    staff_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    staff_level TEXT DEFAULT 'new',
                    time_created TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    last_login TEXT DEFAULT '',
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT DEFAULT ''
                )
            """)
            
            # Message logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_logs (
                    log_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    model TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    research_model BOOLEAN DEFAULT 0,
                    time TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    processing_time_ms INTEGER DEFAULT 0,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)
            
            # Sessions table for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_type TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    ip_address TEXT DEFAULT '',
                    user_agent TEXT DEFAULT ''
                )
            """)
            
            # API usage tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    usage_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT DEFAULT '',
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT DEFAULT ''
                )
            """)
            
            # Batch message logs for high performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_message_logs (
                    batch_id TEXT PRIMARY KEY,
                    messages TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    processed BOOLEAN DEFAULT 0
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_key ON users(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_logs_username ON message_logs(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_logs_time ON message_logs(time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_username ON api_usage(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp)")
            
        logger.info("Database initialized successfully")
    
    def generate_api_key(self) -> str:
        """Generate unique API key"""
        while True:
            key = f"pe-{secrets.token_urlsafe(32)}"
            with self.get_cursor() as cursor:
                cursor.execute("SELECT key FROM users WHERE key = ?", (key,))
                if not cursor.fetchone():
                    return key
    
    def create_user(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create new user"""
        try:
            # Check if username or email already exists
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT username FROM users WHERE username = ? OR email = ?",
                    (user_data['username'], user_data['email'])
                )
                if cursor.fetchone():
                    return False, "Username or email already exists"
                
                # Generate API key
                api_key = self.generate_api_key()
                
                # Create user
                cursor.execute("""
                    INSERT INTO users (
                        username, name, email, password_hash, about_me, hobbies,
                        user_type, time_created, subscription_plan, credits, limits,
                        access_rtype, level, additional_notes, key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_data['username'],
                    user_data['name'],
                    user_data['email'],
                    user_data['password_hash'],
                    user_data.get('about_me', ''),
                    user_data.get('hobbies', ''),
                    user_data.get('user_type', 'Personal'),
                    datetime.now().isoformat(),
                    user_data.get('subscription_plan', 'free'),
                    user_data.get('credits', '{"main":5, "reset":5}'),
                    user_data.get('limits', '{"conversation_limit":10, "reset":10}'),
                    user_data.get('access_rtype', '["bpe","tot"]'),
                    user_data.get('level', 'low'),
                    user_data.get('additional_notes', ''),
                    api_key
                ))
                
                return True, api_key
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, str(e)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by username: {e}")
            return None
    
    def get_user_by_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user by API key"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE key = ? AND is_active = 1", (api_key,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by key: {e}")
            return None
    
    def update_user_limits(self, username: str, limits_update: Dict[str, int]) -> bool:
        """Update user conversation limits"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT limits FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                current_limits = json.loads(row['limits'])
                current_limits.update(limits_update)
                
                cursor.execute(
                    "UPDATE users SET limits = ? WHERE username = ?",
                    (json.dumps(current_limits), username)
                )
                return True
        except Exception as e:
            logger.error(f"Error updating user limits: {e}")
            return False
    
    def reset_daily_limits(self) -> int:
        """Reset daily conversation limits for all users"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT username, limits FROM users WHERE is_active = 1")
                users = cursor.fetchall()
                
                updated_count = 0
                for user in users:
                    limits = json.loads(user['limits'])
                    limits['conversation_limit'] = limits['reset']
                    
                    cursor.execute(
                        "UPDATE users SET limits = ? WHERE username = ?",
                        (json.dumps(limits), user['username'])
                    )
                    updated_count += 1
                
                return updated_count
        except Exception as e:
            logger.error(f"Error resetting daily limits: {e}")
            return 0
    
    def log_message(self, log_data: Dict[str, Any]) -> bool:
        """Log message to database"""
        try:
            log_id = secrets.token_urlsafe(16)
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO message_logs (
                        log_id, username, email, model, messages, research_model, 
                        time, tokens_used, processing_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_id,
                    log_data['username'],
                    log_data['email'],
                    log_data['model'],
                    json.dumps(log_data['messages']),
                    log_data.get('research_model', False),
                    datetime.now().isoformat(),
                    log_data.get('tokens_used', 0),
                    log_data.get('processing_time_ms', 0)
                ))
                return True
        except Exception as e:
            logger.error(f"Error logging message: {e}")
            return False
    
    def create_session(self, username: str, user_type: str = "user", ip_address: str = "", user_agent: str = "") -> str:
        """Create user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, username, user_type, created_at, expires_at, 
                        ip_address, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, username, user_type, datetime.now().isoformat(),
                    expires_at, ip_address, user_agent
                ))
                return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return ""
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE session_id = ? AND is_active = 1 AND expires_at > ?
                """, (session_id, datetime.now().isoformat()))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def delete_user(self, username: str, deleted_by: str = "user") -> bool:
        """Delete user (move to backup table)"""
        try:
            with self.get_cursor() as cursor:
                # Get user data
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                if not user:
                    return False
                
                # Move to deleted_users table
                cursor.execute("""
                    INSERT INTO deleted_users (
                        username, name, email, password_hash, about_me, hobbies,
                        user_type, time_created, subscription_plan, credits, limits,
                        access_rtype, level, additional_notes, key, deleted_at, deleted_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user['username'], user['name'], user['email'], user['password_hash'],
                    user['about_me'], user['hobbies'], user['user_type'], user['time_created'],
                    user['subscription_plan'], user['credits'], user['limits'], user['access_rtype'],
                    user['level'], user['additional_notes'], user['key'],
                    datetime.now().isoformat(), deleted_by
                ))
                
                # Delete from main table
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                
                # Deactivate sessions
                cursor.execute("UPDATE sessions SET is_active = 0 WHERE username = ?", (username,))
                
                return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()


# Global database instance
db_manager = DatabaseManager()