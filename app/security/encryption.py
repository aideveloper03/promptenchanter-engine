"""
Advanced Encryption and Security Utilities
"""
import os
import secrets
import hashlib
import base64
import json
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from passlib.context import CryptContext
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityManager:
    """Advanced security manager for encryption and authentication"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or os.getenv("MASTER_KEY", self._generate_master_key())
        self._fernet = self._create_fernet()
        self.jwt_secret = os.getenv("JWT_SECRET", secrets.token_urlsafe(64))
        self.jwt_algorithm = "HS256"
        
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet encryption instance"""
        key = base64.urlsafe_b64encode(self.master_key.encode()[:32].ljust(32, b'\0'))
        return Fernet(key)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one number"
        
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(char.islower() for char in password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for common weak passwords
        weak_passwords = [
            "password", "12345678", "qwerty", "abc123", "password123",
            "admin", "letmein", "welcome", "monkey", "dragon"
        ]
        
        if password.lower() in weak_passwords:
            return False, "Password is too common. Please choose a stronger password"
        
        return True, "Password is strong"
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure transmission"""
        return self.encrypt_data(api_key)
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key"""
        return self.decrypt_data(encrypted_key)
    
    def generate_jwt_token(self, payload: Dict[str, Any], expires_hours: int = 24) -> str:
        """Generate JWT token"""
        payload_copy = payload.copy()
        payload_copy['exp'] = datetime.utcnow() + timedelta(hours=expires_hours)
        payload_copy['iat'] = datetime.utcnow()
        
        return jwt.encode(payload_copy, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def generate_secure_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF protection token"""
        return secrets.token_urlsafe(32)
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash sensitive data with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        
        key = kdf.derive(data.encode())
        hashed = base64.urlsafe_b64encode(key).decode()
        
        return hashed, salt
    
    def verify_hashed_data(self, data: str, hashed_data: str, salt: str) -> bool:
        """Verify hashed data"""
        try:
            new_hash, _ = self.hash_sensitive_data(data, salt)
            return new_hash == hashed_data
        except Exception as e:
            logger.error(f"Hash verification error: {e}")
            return False
    
    def generate_api_key_pair(self) -> Tuple[str, str]:
        """Generate RSA key pair for API key encryption"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        public_key = private_key.public_key()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return private_pem, public_pem
    
    def encrypt_with_public_key(self, data: str, public_key_pem: str) -> str:
        """Encrypt data with RSA public key"""
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        
        encrypted = public_key.encrypt(
            data.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_with_private_key(self, encrypted_data: str, private_key_pem: str) -> str:
        """Decrypt data with RSA private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted.decode()
    
    def create_secure_headers(self) -> Dict[str, str]:
        """Create secure HTTP headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


# Global security manager instance
security_manager = SecurityManager()


class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self):
        self.attempts = {}
        self.blocked_ips = set()
        self.suspicious_patterns = {}
    
    def check_rate_limit(self, identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> Tuple[bool, int]:
        """Check if identifier is rate limited"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier] 
            if attempt > window_start
        ]
        
        current_attempts = len(self.attempts[identifier])
        
        if current_attempts >= max_attempts:
            return False, max_attempts - current_attempts
        
        return True, max_attempts - current_attempts
    
    def record_attempt(self, identifier: str):
        """Record an attempt"""
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        self.attempts[identifier].append(datetime.now())
    
    def block_ip(self, ip_address: str):
        """Block IP address"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"IP address blocked: {ip_address}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips
    
    def detect_suspicious_pattern(self, identifier: str, pattern_type: str) -> bool:
        """Detect suspicious patterns"""
        if identifier not in self.suspicious_patterns:
            self.suspicious_patterns[identifier] = {}
        
        if pattern_type not in self.suspicious_patterns[identifier]:
            self.suspicious_patterns[identifier][pattern_type] = []
        
        now = datetime.now()
        self.suspicious_patterns[identifier][pattern_type].append(now)
        
        # Clean old patterns (last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.suspicious_patterns[identifier][pattern_type] = [
            timestamp for timestamp in self.suspicious_patterns[identifier][pattern_type]
            if timestamp > cutoff
        ]
        
        # Check if pattern is suspicious
        recent_count = len(self.suspicious_patterns[identifier][pattern_type])
        
        # Define thresholds for different patterns
        thresholds = {
            "failed_login": 10,
            "api_abuse": 100,
            "suspicious_request": 20
        }
        
        threshold = thresholds.get(pattern_type, 50)
        
        if recent_count >= threshold:
            logger.warning(f"Suspicious pattern detected: {identifier} - {pattern_type}")
            return True
        
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()