"""
Firewall and IP filtering functionality
"""
import asyncio
import ipaddress
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from app.database.database import get_db_session
from app.database.models import IPWhitelist, SecurityLog
from app.security.encryption import ip_security_manager
from app.utils.logger import get_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class FirewallManager:
    """Advanced firewall and security manager"""
    
    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.rate_limit_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.temp_blocks: Dict[str, datetime] = {}
        self.whitelist_cache: Dict[str, bool] = {}
        self.whitelist_cache_ttl: datetime = datetime.now()
        
        # Configuration
        self.max_requests_per_minute = 60
        self.max_failed_attempts = 5
        self.block_duration_minutes = 15
        self.whitelist_cache_duration = 300  # 5 minutes
    
    async def is_ip_allowed(self, ip_address: str, session: AsyncSession) -> Tuple[bool, str]:
        """Check if IP address is allowed to access the API"""
        
        # Check if IP is in temporary block list
        if ip_address in self.temp_blocks:
            block_until = self.temp_blocks[ip_address]
            if datetime.now() < block_until:
                return False, "IP temporarily blocked due to suspicious activity"
            else:
                # Remove expired block
                del self.temp_blocks[ip_address]
        
        # Check permanent block list
        if ip_address in self.blocked_ips:
            return False, "IP permanently blocked"
        
        # Check whitelist (with caching)
        if await self._is_whitelisted(ip_address, session):
            return True, "IP whitelisted"
        
        # Check rate limiting
        if not self._check_rate_limit(ip_address):
            await self._log_security_event(
                "rate_limit_exceeded",
                ip_address=ip_address,
                details={"requests_per_minute": len(self.rate_limit_tracker[ip_address])}
            )
            return False, "Rate limit exceeded"
        
        return True, "IP allowed"
    
    async def _is_whitelisted(self, ip_address: str, session: AsyncSession) -> bool:
        """Check if IP is in whitelist with caching"""
        
        # Check cache first
        if datetime.now() < self.whitelist_cache_ttl:
            if ip_address in self.whitelist_cache:
                return self.whitelist_cache[ip_address]
        else:
            # Clear expired cache
            self.whitelist_cache.clear()
            self.whitelist_cache_ttl = datetime.now() + timedelta(seconds=self.whitelist_cache_duration)
        
        # Query database
        try:
            result = await session.execute(
                select(IPWhitelist).where(
                    IPWhitelist.is_active == True,
                    (IPWhitelist.expires_at.is_(None) | (IPWhitelist.expires_at > datetime.now()))
                )
            )
            whitelist_entries = result.scalars().all()
            
            for entry in whitelist_entries:
                # Check exact IP match
                if entry.ip_address == ip_address:
                    self.whitelist_cache[ip_address] = True
                    return True
                
                # Check IP range match
                if entry.ip_range:
                    try:
                        if ip_security_manager.is_ip_in_range(ip_address, entry.ip_range):
                            self.whitelist_cache[ip_address] = True
                            return True
                    except Exception:
                        continue
            
            self.whitelist_cache[ip_address] = False
            return False
            
        except Exception as e:
            logger.error(f"Error checking IP whitelist: {e}")
            return False
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check if IP is within rate limits"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        while self.rate_limit_tracker[ip_address] and self.rate_limit_tracker[ip_address][0] < minute_ago:
            self.rate_limit_tracker[ip_address].popleft()
        
        # Add current request
        self.rate_limit_tracker[ip_address].append(now)
        
        # Check if limit exceeded
        return len(self.rate_limit_tracker[ip_address]) <= self.max_requests_per_minute
    
    async def record_failed_attempt(self, ip_address: str, reason: str = "authentication_failed"):
        """Record failed authentication attempt"""
        self.failed_attempts[ip_address] += 1
        
        await self._log_security_event(
            "failed_attempt",
            ip_address=ip_address,
            details={
                "reason": reason,
                "attempt_count": self.failed_attempts[ip_address]
            }
        )
        
        # Check if IP should be temporarily blocked
        if self.failed_attempts[ip_address] >= self.max_failed_attempts:
            block_until = datetime.now() + timedelta(minutes=self.block_duration_minutes)
            self.temp_blocks[ip_address] = block_until
            
            await self._log_security_event(
                "ip_temporarily_blocked",
                ip_address=ip_address,
                details={
                    "failed_attempts": self.failed_attempts[ip_address],
                    "blocked_until": block_until.isoformat()
                },
                severity="warning"
            )
            
            # Reset failed attempts counter
            self.failed_attempts[ip_address] = 0
    
    async def record_successful_attempt(self, ip_address: str):
        """Record successful authentication attempt"""
        # Reset failed attempts counter
        if ip_address in self.failed_attempts:
            del self.failed_attempts[ip_address]
    
    async def add_to_permanent_blocklist(self, ip_address: str, reason: str = "manual_block"):
        """Add IP to permanent block list"""
        self.blocked_ips.add(ip_address)
        
        await self._log_security_event(
            "ip_permanently_blocked",
            ip_address=ip_address,
            details={"reason": reason},
            severity="critical"
        )
    
    async def remove_from_blocklist(self, ip_address: str):
        """Remove IP from block lists"""
        self.blocked_ips.discard(ip_address)
        if ip_address in self.temp_blocks:
            del self.temp_blocks[ip_address]
        if ip_address in self.failed_attempts:
            del self.failed_attempts[ip_address]
    
    async def _log_security_event(
        self, 
        event_type: str, 
        ip_address: str = None, 
        user_id: int = None,
        username: str = None,
        details: dict = None,
        severity: str = "info"
    ):
        """Log security event to database"""
        try:
            async with get_db_session() as session:
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
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def get_security_stats(self) -> dict:
        """Get current security statistics"""
        return {
            "blocked_ips_count": len(self.blocked_ips),
            "temp_blocked_ips_count": len(self.temp_blocks),
            "active_rate_limits": len([ip for ip, requests in self.rate_limit_tracker.items() if len(requests) > 0]),
            "failed_attempts_tracking": len(self.failed_attempts),
            "whitelist_cache_size": len(self.whitelist_cache)
        }


class FirewallMiddleware:
    """FastAPI middleware for firewall functionality"""
    
    def __init__(self, firewall_manager: FirewallManager):
        self.firewall_manager = firewall_manager
    
    async def __call__(self, request: Request, call_next):
        # Skip firewall for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = ip_security_manager.get_client_ip(request)
        
        # Check if IP is allowed
        async with get_db_session() as session:
            allowed, reason = await self.firewall_manager.is_ip_allowed(client_ip, session)
        
        if not allowed:
            logger.warning(f"Blocked request from {client_ip}: {reason}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {reason}"
            )
        
        # Add IP to request state for later use
        request.state.client_ip = client_ip
        
        # Process request
        response = await call_next(request)
        
        return response


# Global firewall manager instance
firewall_manager = FirewallManager()