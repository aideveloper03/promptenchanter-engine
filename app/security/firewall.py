"""
Advanced Firewall and IP Management System
"""
import ipaddress
import json
import logging
from typing import Set, List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    ALLOWED = "allowed"
    WHITELISTED = "whitelisted"


@dataclass
class IPRule:
    ip_range: str
    access_level: AccessLevel
    reason: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    created_by: str = "system"
    active: bool = True


@dataclass
class SecurityEvent:
    timestamp: datetime
    ip_address: str
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    user_agent: str = ""
    endpoint: str = ""
    blocked: bool = False


class IPFirewall:
    """Advanced IP-based firewall system"""
    
    def __init__(self, config_file: str = "firewall_config.json"):
        self.config_file = Path(config_file)
        self.rules: List[IPRule] = []
        self.security_events: List[SecurityEvent] = []
        self.blocked_ips: Set[str] = set()
        self.whitelisted_ips: Set[str] = set()
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.suspicious_ips: Dict[str, int] = {}
        self._lock = threading.RLock()
        
        # Default settings
        self.whitelist_enabled = False  # Disabled by default as requested
        self.auto_block_enabled = True
        self.rate_limit_per_minute = 60
        self.rate_limit_per_hour = 1000
        self.suspicious_threshold = 10
        
        self._load_config()
        self._load_default_rules()
    
    def _load_config(self):
        """Load firewall configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.whitelist_enabled = config.get('whitelist_enabled', False)
                    self.auto_block_enabled = config.get('auto_block_enabled', True)
                    self.rate_limit_per_minute = config.get('rate_limit_per_minute', 60)
                    self.rate_limit_per_hour = config.get('rate_limit_per_hour', 1000)
                    
                    # Load rules
                    for rule_data in config.get('rules', []):
                        rule = IPRule(
                            ip_range=rule_data['ip_range'],
                            access_level=AccessLevel(rule_data['access_level']),
                            reason=rule_data['reason'],
                            created_at=datetime.fromisoformat(rule_data['created_at']),
                            expires_at=datetime.fromisoformat(rule_data['expires_at']) if rule_data.get('expires_at') else None,
                            created_by=rule_data.get('created_by', 'system'),
                            active=rule_data.get('active', True)
                        )
                        self.rules.append(rule)
                        
                        # Update quick access sets
                        if rule.access_level == AccessLevel.BLOCKED:
                            self.blocked_ips.add(rule.ip_range)
                        elif rule.access_level == AccessLevel.WHITELISTED:
                            self.whitelisted_ips.add(rule.ip_range)
                            
        except Exception as e:
            logger.error(f"Error loading firewall config: {e}")
    
    def _save_config(self):
        """Save firewall configuration"""
        try:
            config = {
                'whitelist_enabled': self.whitelist_enabled,
                'auto_block_enabled': self.auto_block_enabled,
                'rate_limit_per_minute': self.rate_limit_per_minute,
                'rate_limit_per_hour': self.rate_limit_per_hour,
                'rules': []
            }
            
            for rule in self.rules:
                rule_data = asdict(rule)
                rule_data['access_level'] = rule.access_level.value
                rule_data['created_at'] = rule.created_at.isoformat()
                if rule.expires_at:
                    rule_data['expires_at'] = rule.expires_at.isoformat()
                config['rules'].append(rule_data)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving firewall config: {e}")
    
    def _load_default_rules(self):
        """Load default security rules"""
        default_blocked_ranges = [
            # Known malicious IP ranges (examples)
            "10.0.0.0/8",      # Private networks (if not internal)
            "172.16.0.0/12",   # Private networks
            "192.168.0.0/16",  # Private networks
            # Add more known bad ranges here
        ]
        
        # Only add if not already present
        existing_ranges = {rule.ip_range for rule in self.rules}
        
        for ip_range in default_blocked_ranges:
            if ip_range not in existing_ranges:
                # Don't auto-block private networks - this was just an example
                # In production, you'd want to be more careful about this
                pass
    
    def is_ip_allowed(self, ip_address: str) -> Tuple[bool, str]:
        """Check if IP address is allowed"""
        with self._lock:
            try:
                ip = ipaddress.ip_address(ip_address)
                
                # Check if whitelist is enabled
                if self.whitelist_enabled:
                    if not self._is_whitelisted(ip_address):
                        return False, "IP not in whitelist"
                
                # Check explicit rules
                for rule in self.rules:
                    if not rule.active:
                        continue
                        
                    # Check if rule has expired
                    if rule.expires_at and datetime.now() > rule.expires_at:
                        rule.active = False
                        continue
                    
                    try:
                        if ip in ipaddress.ip_network(rule.ip_range, strict=False):
                            if rule.access_level == AccessLevel.BLOCKED:
                                return False, f"IP blocked: {rule.reason}"
                            elif rule.access_level == AccessLevel.WHITELISTED:
                                return True, "IP whitelisted"
                            elif rule.access_level == AccessLevel.RESTRICTED:
                                # Additional checks for restricted IPs
                                if not self._check_rate_limit(ip_address):
                                    return False, "Rate limit exceeded for restricted IP"
                    except ValueError:
                        # Invalid IP range in rule, skip
                        continue
                
                # Check rate limits
                if not self._check_rate_limit(ip_address):
                    return False, "Rate limit exceeded"
                
                # Check suspicious activity
                if self._is_suspicious(ip_address):
                    return False, "Suspicious activity detected"
                
                return True, "IP allowed"
                
            except ValueError:
                return False, "Invalid IP address"
    
    def _is_whitelisted(self, ip_address: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            ip = ipaddress.ip_address(ip_address)
            for whitelisted_range in self.whitelisted_ips:
                try:
                    if ip in ipaddress.ip_network(whitelisted_range, strict=False):
                        return True
                except ValueError:
                    continue
            return False
        except ValueError:
            return False
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check rate limits for IP"""
        now = datetime.now()
        
        if ip_address not in self.rate_limits:
            self.rate_limits[ip_address] = []
        
        # Clean old requests
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.rate_limits[ip_address] = [
            req_time for req_time in self.rate_limits[ip_address]
            if req_time > hour_ago
        ]
        
        # Check limits
        recent_requests = [
            req_time for req_time in self.rate_limits[ip_address]
            if req_time > minute_ago
        ]
        
        if len(recent_requests) >= self.rate_limit_per_minute:
            return False
        
        if len(self.rate_limits[ip_address]) >= self.rate_limit_per_hour:
            return False
        
        # Record this request
        self.rate_limits[ip_address].append(now)
        return True
    
    def _is_suspicious(self, ip_address: str) -> bool:
        """Check if IP shows suspicious behavior"""
        return self.suspicious_ips.get(ip_address, 0) >= self.suspicious_threshold
    
    def add_rule(self, ip_range: str, access_level: AccessLevel, reason: str, 
                 created_by: str = "admin", expires_hours: Optional[int] = None) -> bool:
        """Add firewall rule"""
        with self._lock:
            try:
                # Validate IP range
                ipaddress.ip_network(ip_range, strict=False)
                
                expires_at = None
                if expires_hours:
                    expires_at = datetime.now() + timedelta(hours=expires_hours)
                
                rule = IPRule(
                    ip_range=ip_range,
                    access_level=access_level,
                    reason=reason,
                    created_at=datetime.now(),
                    expires_at=expires_at,
                    created_by=created_by
                )
                
                self.rules.append(rule)
                
                # Update quick access sets
                if access_level == AccessLevel.BLOCKED:
                    self.blocked_ips.add(ip_range)
                elif access_level == AccessLevel.WHITELISTED:
                    self.whitelisted_ips.add(ip_range)
                
                self._save_config()
                logger.info(f"Firewall rule added: {ip_range} -> {access_level.value}")
                return True
                
            except ValueError as e:
                logger.error(f"Invalid IP range: {ip_range} - {e}")
                return False
            except Exception as e:
                logger.error(f"Error adding firewall rule: {e}")
                return False
    
    def remove_rule(self, ip_range: str) -> bool:
        """Remove firewall rule"""
        with self._lock:
            try:
                for i, rule in enumerate(self.rules):
                    if rule.ip_range == ip_range:
                        removed_rule = self.rules.pop(i)
                        
                        # Update quick access sets
                        if removed_rule.access_level == AccessLevel.BLOCKED:
                            self.blocked_ips.discard(ip_range)
                        elif removed_rule.access_level == AccessLevel.WHITELISTED:
                            self.whitelisted_ips.discard(ip_range)
                        
                        self._save_config()
                        logger.info(f"Firewall rule removed: {ip_range}")
                        return True
                
                return False
                
            except Exception as e:
                logger.error(f"Error removing firewall rule: {e}")
                return False
    
    def block_ip(self, ip_address: str, reason: str, created_by: str = "system", hours: int = 24) -> bool:
        """Block IP address"""
        return self.add_rule(ip_address, AccessLevel.BLOCKED, reason, created_by, hours)
    
    def whitelist_ip(self, ip_address: str, reason: str, created_by: str = "admin") -> bool:
        """Whitelist IP address"""
        return self.add_rule(ip_address, AccessLevel.WHITELISTED, reason, created_by)
    
    def record_security_event(self, ip_address: str, event_type: str, severity: str, 
                            description: str, user_agent: str = "", endpoint: str = "", 
                            blocked: bool = False):
        """Record security event"""
        with self._lock:
            event = SecurityEvent(
                timestamp=datetime.now(),
                ip_address=ip_address,
                event_type=event_type,
                severity=severity,
                description=description,
                user_agent=user_agent,
                endpoint=endpoint,
                blocked=blocked
            )
            
            self.security_events.append(event)
            
            # Increment suspicious counter
            if severity in ['high', 'critical']:
                self.suspicious_ips[ip_address] = self.suspicious_ips.get(ip_address, 0) + 1
                
                # Auto-block if threshold reached
                if self.auto_block_enabled and self.suspicious_ips[ip_address] >= self.suspicious_threshold:
                    self.block_ip(ip_address, f"Auto-blocked due to suspicious activity: {description}")
            
            # Keep only recent events (last 30 days)
            cutoff = datetime.now() - timedelta(days=30)
            self.security_events = [
                event for event in self.security_events 
                if event.timestamp > cutoff
            ]
            
            logger.warning(f"Security event: {event_type} from {ip_address} - {description}")
    
    def get_security_events(self, hours: int = 24) -> List[SecurityEvent]:
        """Get recent security events"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [event for event in self.security_events if event.timestamp > cutoff]
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of blocked IPs"""
        return list(self.blocked_ips)
    
    def get_whitelisted_ips(self) -> List[str]:
        """Get list of whitelisted IPs"""
        return list(self.whitelisted_ips)
    
    def enable_whitelist_mode(self):
        """Enable whitelist mode"""
        with self._lock:
            self.whitelist_enabled = True
            self._save_config()
            logger.info("Whitelist mode enabled")
    
    def disable_whitelist_mode(self):
        """Disable whitelist mode"""
        with self._lock:
            self.whitelist_enabled = False
            self._save_config()
            logger.info("Whitelist mode disabled")
    
    def get_stats(self) -> Dict[str, any]:
        """Get firewall statistics"""
        with self._lock:
            recent_events = self.get_security_events(24)
            
            return {
                "whitelist_enabled": self.whitelist_enabled,
                "auto_block_enabled": self.auto_block_enabled,
                "total_rules": len(self.rules),
                "blocked_ips_count": len(self.blocked_ips),
                "whitelisted_ips_count": len(self.whitelisted_ips),
                "suspicious_ips_count": len(self.suspicious_ips),
                "recent_events_24h": len(recent_events),
                "blocked_events_24h": len([e for e in recent_events if e.blocked]),
                "rate_limit_per_minute": self.rate_limit_per_minute,
                "rate_limit_per_hour": self.rate_limit_per_hour
            }


# Global firewall instance
firewall = IPFirewall()