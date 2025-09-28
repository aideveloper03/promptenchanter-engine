"""
Safe database logging utilities that gracefully handle database write failures
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SafeDatabaseLogger:
    """
    A database logger that gracefully handles write failures and provides
    fallback logging mechanisms when the database is read-only or unavailable.
    """
    
    def __init__(self):
        self.fallback_enabled = True
        self.failed_writes_count = 0
        self.max_failed_writes = 5  # After 5 failures, stop trying for a while
        
    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> bool:
        """
        Safely log a security event to the database with fallback to file logging.
        
        Returns:
            bool: True if successfully logged to database, False if fallback used
        """
        
        # If we've had too many failed writes, use fallback only
        if self.failed_writes_count >= self.max_failed_writes:
            self._log_to_fallback(event_type, user_id, username, ip_address, details, severity)
            return False
        
        try:
            # Try to log to database
            from app.database.database import get_db_session_context
            from app.database.models import SecurityLog
            
            async with get_db_session_context() as session:
                security_log = SecurityLog(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address,
                    details=details,
                    severity=severity
                )
                session.add(security_log)
                await session.commit()
                
                # Reset failed writes counter on success
                self.failed_writes_count = 0
                return True
                
        except Exception as e:
            self.failed_writes_count += 1
            logger.warning(
                f"Failed to log security event to database (attempt {self.failed_writes_count}): {e}"
            )
            
            # Use fallback logging
            self._log_to_fallback(event_type, user_id, username, ip_address, details, severity)
            return False
    
    def _log_to_fallback(
        self,
        event_type: str,
        user_id: Optional[int],
        username: Optional[str],
        ip_address: Optional[str],
        details: Optional[Dict[str, Any]],
        severity: str
    ):
        """Log security event to fallback mechanism (structured logging)"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "details": details,
            "severity": severity,
            "source": "fallback_security_logger"
        }
        
        # Use structured logging as fallback
        if severity == "critical":
            logger.critical("Security Event", **log_entry)
        elif severity == "warning":
            logger.warning("Security Event", **log_entry)
        elif severity == "error":
            logger.error("Security Event", **log_entry)
        else:
            logger.info("Security Event", **log_entry)
    
    def reset_failed_writes(self):
        """Reset the failed writes counter (can be called periodically)"""
        self.failed_writes_count = 0

# Global instance
safe_db_logger = SafeDatabaseLogger()