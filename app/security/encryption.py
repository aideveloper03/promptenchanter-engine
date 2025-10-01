"""
Encryption utilities for sensitive data protection
"""
import os
import base64
import secrets
from typing import Optional, Tuple, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from app.config.settings import get_settings

settings = get_settings()


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        self._master_key = self._get_or_create_master_key()
        self._fernet = Fernet(self._master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = "master.key"
        
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        if not data:
            return ""
        
        encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        if not encrypted_data:
            return ""
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception:
            raise ValueError("Failed to decrypt data")
    
    def encrypt_json(self, data: dict) -> str:
        """Encrypt JSON data"""
        import json
        json_str = json.dumps(data, separators=(',', ':'))
        return self.encrypt(json_str)
    
    def decrypt_json(self, encrypted_data: str) -> dict:
        """Decrypt JSON data"""
        import json
        decrypted_str = self.decrypt(encrypted_data)
        return json.loads(decrypted_str)


class PasswordManager:
    """Manages password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using argon2id"""
        from passlib.context import CryptContext
        
        # Configure Argon2id with secure parameters
        # time_cost=3: Number of iterations (higher = slower but more secure)
        # memory_cost=65536: Memory usage in KiB (64 MB)
        # parallelism=1: Number of parallel threads
        pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__time_cost=3,
            argon2__memory_cost=65536,  # 64 MB
            argon2__parallelism=1,
            argon2__hash_len=32,  # 32 byte hash output
            argon2__salt_len=16   # 16 byte salt
        )
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash (supports both argon2id and legacy bcrypt)"""
        from passlib.context import CryptContext
        
        # Support both argon2id (new) and bcrypt (legacy) for backward compatibility
        pwd_context = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="auto",
            # Argon2id configuration
            argon2__time_cost=3,
            argon2__memory_cost=65536,
            argon2__parallelism=1,
            argon2__hash_len=32,
            argon2__salt_len=16
        )
        
        # For bcrypt compatibility, apply the same truncation logic as before
        verification_password = plain_password
        if hashed_password.startswith(('$2a$', '$2b$', '$2x$', '$2y$')):  # bcrypt hash
            if len(plain_password.encode('utf-8')) > 72:
                # Truncate to 72 bytes while preserving UTF-8 encoding
                password_bytes = plain_password.encode('utf-8')[:72]
                # Ensure we don't break UTF-8 encoding at byte boundary
                try:
                    verification_password = password_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # If truncation broke UTF-8, try shorter lengths
                    for i in range(71, 60, -1):
                        try:
                            verification_password = plain_password.encode('utf-8')[:i].decode('utf-8')
                            break
                        except UnicodeDecodeError:
                            continue
        
        return pwd_context.verify(verification_password, hashed_password)
    
    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """Check if password hash needs to be upgraded to argon2id"""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="auto",
            argon2__time_cost=3,
            argon2__memory_cost=65536,
            argon2__parallelism=1,
            argon2__hash_len=32,
            argon2__salt_len=16
        )
        
        return pwd_context.needs_update(hashed_password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        # Set reasonable maximum length (argon2id can handle much longer passwords)
        password_bytes = len(password.encode('utf-8'))
        if password_bytes > 1024:  # 1KB limit - reasonable for passwords
            errors.append(f"Password is too long ({password_bytes} bytes). Maximum is 1024 bytes")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least 1 number")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least 1 uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least 1 lowercase letter")
        
        # Check for common weak passwords
        weak_passwords = [
            "password", "123456", "123456789", "qwerty", "abc123",
            "password123", "admin", "letmein", "welcome", "monkey"
        ]
        
        if password.lower() in weak_passwords:
            errors.append("Password is too common and easily guessable")
        
        return len(errors) == 0, errors


class TokenManager:
    """Manages secure token generation and validation"""
    
    @staticmethod
    def generate_api_key(prefix: str = "pe-") -> str:
        """Generate secure API key"""
        # Generate 32 random bytes and encode as base64
        random_bytes = secrets.token_bytes(32)
        key_suffix = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        return f"{prefix}{key_suffix}"
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(64)


class IPSecurityManager:
    """Manages IP-based security features"""
    
    @staticmethod
    def is_valid_ip(ip_address: str) -> bool:
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_ip_in_range(ip_address: str, ip_range: str) -> bool:
        """Check if IP is in CIDR range"""
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_address)
            network = ipaddress.ip_network(ip_range, strict=False)
            return ip in network
        except ValueError:
            return False
    
    @staticmethod
    def get_client_ip(request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


# Global instances
encryption_manager = EncryptionManager()
password_manager = PasswordManager()
token_manager = TokenManager()
ip_security_manager = IPSecurityManager()