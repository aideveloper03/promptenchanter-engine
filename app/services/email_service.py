"""
Email service for PromptEnchanter
Handles email verification and other email communications
"""
import asyncio
import smtplib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from app.config.settings import get_settings
from app.utils.logger import get_logger
from app.database.mongodb import get_mongodb_collection, MongoDBUtils

logger = get_logger(__name__)
settings = get_settings()


class EmailService:
    """Service for handling email operations"""
    
    def __init__(self):
        self.smtp_configured = bool(
            settings.smtp_host and 
            settings.smtp_username and 
            settings.smtp_password
        )
        self._config_validated = False
        self._config_error = None
    
    async def validate_smtp_config(self) -> Tuple[bool, str]:
        """Validate SMTP configuration before sending emails"""
        
        if not self.smtp_configured:
            return False, "SMTP not configured. Missing: host, username, or password"
        
        # Return cached result if already validated
        if self._config_validated:
            return True, "SMTP configured correctly"
        
        if self._config_error:
            return False, self._config_error
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            def test_smtp():
                try:
                    if settings.smtp_use_tls:
                        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
                        server.starttls()
                    else:
                        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
                    
                    server.login(settings.smtp_username, settings.smtp_password)
                    server.quit()
                    return True, "SMTP configured correctly"
                except smtplib.SMTPAuthenticationError as e:
                    return False, f"SMTP authentication failed: {str(e)}. Check username/password"
                except smtplib.SMTPConnectError as e:
                    return False, f"SMTP connection failed: {str(e)}. Check host/port"
                except Exception as e:
                    return False, f"SMTP configuration error: {str(e)}"
            
            success, message = await loop.run_in_executor(None, test_smtp)
            
            if success:
                self._config_validated = True
            else:
                self._config_error = message
            
            return success, message
            
        except Exception as e:
            error_msg = f"SMTP validation error: {str(e)}"
            self._config_error = error_msg
            return False, error_msg
    
    async def send_verification_email(self, user_id: str, email: str, name: str) -> Dict[str, Any]:
        """Send email verification with OTP"""
        
        if not settings.email_verification_enabled:
            logger.info("Email verification is disabled, skipping email send")
            return {"success": True, "message": "Email verification is disabled"}
        
        # Validate SMTP configuration
        if not self.smtp_configured:
            logger.warning("SMTP not configured properly. Missing: host=%s, username=%s, password=%s", 
                         bool(settings.smtp_host), bool(settings.smtp_username), bool(settings.smtp_password))
            # Return success but log the issue - don't fail registration due to email config
            return {"success": True, "message": "Email service not configured, verification skipped"}
        
        # Test SMTP connection before attempting to send
        config_valid, config_message = await self.validate_smtp_config()
        if not config_valid:
            logger.error(f"SMTP configuration invalid: {config_message}")
            return {
                "success": False, 
                "message": f"Email service configuration error: {config_message}"
            }
        
        try:
            # Generate OTP
            otp_code = self._generate_otp()
            
            # Check rate limiting
            verification_collection = await get_mongodb_collection('email_verification')
            
            # Check if user has exceeded daily limit
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = await verification_collection.count_documents({
                "user_id": user_id,
                "created_at": {"$gte": today_start}
            })
            
            if today_count >= settings.email_verification_resend_limit_per_day:
                return {
                    "success": False, 
                    "message": f"Daily limit of {settings.email_verification_resend_limit_per_day} verification emails exceeded"
                }
            
            # Create or update verification record
            expires_at = datetime.now() + timedelta(hours=settings.email_verification_token_expiry_hours)
            
            verification_doc = {
                "user_id": user_id,
                "email": email,
                "otp_code": otp_code,
                "expires_at": expires_at,
                "created_at": datetime.now(),
                "attempts": 0,
                "verified": False,
                "resend_count": today_count + 1,
                "last_resend": datetime.now()
            }
            
            # Upsert verification record
            await verification_collection.update_one(
                {"user_id": user_id, "email": email, "verified": False},
                {"$set": verification_doc},
                upsert=True
            )
            
            # Send email
            subject = "Verify Your Email - PromptEnchanter"
            html_content = self._generate_verification_email_html(name, otp_code)
            text_content = self._generate_verification_email_text(name, otp_code)
            
            success = await self._send_email(email, subject, html_content, text_content)
            
            if success:
                logger.info(f"Verification email sent to {email}")
                return {
                    "success": True,
                    "message": "Verification email sent successfully",
                    "expires_at": expires_at.isoformat()
                }
            else:
                logger.warning(f"Failed to send verification email to {email}, but continuing registration")
                # Don't fail the registration due to email issues
                return {
                    "success": True, 
                    "message": "Registration completed, but verification email could not be sent"
                }
                
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            # Don't fail registration due to email issues
            return {
                "success": True, 
                "message": "Registration completed, but verification email could not be sent due to server error"
            }
    
    async def verify_email_otp(self, user_id: str, email: str, otp_code: str) -> Dict[str, Any]:
        """Verify email using OTP code"""
        
        try:
            verification_collection = await get_mongodb_collection('email_verification')
            
            # Find active verification record
            verification_doc = await verification_collection.find_one({
                "user_id": user_id,
                "email": email,
                "verified": False,
                "expires_at": {"$gt": datetime.now()}
            })
            
            if not verification_doc:
                return {
                    "success": False,
                    "message": "No valid verification request found or OTP expired"
                }
            
            # Increment attempts
            await verification_collection.update_one(
                {"_id": verification_doc["_id"]},
                {"$inc": {"attempts": 1}}
            )
            
            # Check if too many attempts
            if verification_doc["attempts"] >= 5:
                return {
                    "success": False,
                    "message": "Too many verification attempts. Please request a new OTP."
                }
            
            # Verify OTP
            if verification_doc["otp_code"] != otp_code:
                return {
                    "success": False,
                    "message": "Invalid OTP code"
                }
            
            # Mark as verified
            await verification_collection.update_one(
                {"_id": verification_doc["_id"]},
                {"$set": {"verified": True, "verified_at": datetime.now()}}
            )
            
            # Update user verification status
            users_collection = await get_mongodb_collection('users')
            await users_collection.update_one(
                {"_id": user_id},
                {"$set": {"is_verified": True, "updated_at": datetime.now()}}
            )
            
            logger.info(f"Email verified successfully for user {user_id}")
            
            return {
                "success": True,
                "message": "Email verified successfully"
            }
            
        except Exception as e:
            logger.error(f"Email verification failed for user {user_id}: {e}")
            return {"success": False, "message": "Email verification failed"}
    
    async def resend_verification_email(self, user_id: str, email: str, name: str) -> Dict[str, Any]:
        """Resend verification email with rate limiting"""
        
        try:
            verification_collection = await get_mongodb_collection('email_verification')
            
            # Check if user already has a verified email
            verified_doc = await verification_collection.find_one({
                "user_id": user_id,
                "email": email,
                "verified": True
            })
            
            if verified_doc:
                return {
                    "success": False,
                    "message": "Email is already verified"
                }
            
            # Check rate limiting for resends
            recent_resend = await verification_collection.find_one({
                "user_id": user_id,
                "email": email,
                "last_resend": {"$gt": datetime.now() - timedelta(minutes=5)}
            })
            
            if recent_resend:
                return {
                    "success": False,
                    "message": "Please wait 5 minutes before requesting another verification email"
                }
            
            # Send new verification email
            return await self.send_verification_email(user_id, email, name)
            
        except Exception as e:
            logger.error(f"Failed to resend verification email: {e}")
            return {"success": False, "message": "Failed to resend verification email"}
    
    def _generate_otp(self) -> str:
        """Generate OTP code"""
        length = settings.email_verification_otp_length
        digits = string.digits
        return ''.join(secrets.choice(digits) for _ in range(length))
    
    def _generate_verification_email_html(self, name: str, otp_code: str) -> str:
        """Generate HTML content for verification email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification - PromptEnchanter</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-code {{ 
                    font-size: 32px; 
                    font-weight: bold; 
                    color: #4f46e5; 
                    text-align: center; 
                    background-color: #e0e7ff; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0;
                    letter-spacing: 4px;
                }}
                .footer {{ text-align: center; color: #6b7280; font-size: 14px; margin-top: 20px; }}
                .warning {{ color: #dc2626; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Email Verification</h1>
                    <p>PromptEnchanter</p>
                </div>
                <div class="content">
                    <h2>Hello {name}!</h2>
                    <p>Thank you for registering with PromptEnchanter. To complete your registration, please verify your email address using the OTP code below:</p>
                    
                    <div class="otp-code">{otp_code}</div>
                    
                    <p>This OTP code will expire in {settings.email_verification_token_expiry_hours} hours.</p>
                    
                    <p class="warning">Important: Do not share this code with anyone. Our team will never ask for your verification code.</p>
                    
                    <p>If you didn't create an account with PromptEnchanter, please ignore this email.</p>
                    
                    <p>Best regards,<br>The PromptEnchanter Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_verification_email_text(self, name: str, otp_code: str) -> str:
        """Generate plain text content for verification email"""
        return f"""
        Email Verification - PromptEnchanter
        
        Hello {name}!
        
        Thank you for registering with PromptEnchanter. To complete your registration, please verify your email address using the OTP code below:
        
        OTP Code: {otp_code}
        
        This OTP code will expire in {settings.email_verification_token_expiry_hours} hours.
        
        Important: Do not share this code with anyone. Our team will never ask for your verification code.
        
        If you didn't create an account with PromptEnchanter, please ignore this email.
        
        Best regards,
        The PromptEnchanter Team
        
        ---
        This is an automated message, please do not reply to this email.
        """
    
    async def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email using SMTP"""
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr(("PromptEnchanter", settings.from_email))
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, 
                self._send_smtp_email, 
                msg, 
                to_email
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _send_smtp_email(self, msg: MIMEMultipart, to_email: str, retry_count: int = 3) -> bool:
        """Send email via SMTP with retry logic (blocking operation)"""
        
        for attempt in range(retry_count):
            try:
                # Create SMTP connection with timeout
                if settings.smtp_use_tls:
                    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
                
                # Enable debug mode if DEBUG is true in settings
                debug_level = 1 if settings.debug else 0
                server.set_debuglevel(debug_level)
                
                # Login with better error handling
                try:
                    server.login(settings.smtp_username, settings.smtp_password)
                except smtplib.SMTPAuthenticationError as auth_error:
                    logger.error(f"SMTP Authentication failed for {settings.smtp_username}: {auth_error}")
                    logger.error("Please check your email credentials and app password settings")
                    server.quit()
                    return False  # Don't retry auth failures
                except smtplib.SMTPException as smtp_error:
                    logger.error(f"SMTP error during login: {smtp_error}")
                    server.quit()
                    return False  # Don't retry protocol errors
                
                # Send email
                server.send_message(msg, to_addrs=[to_email])
                server.quit()
                
                logger.info(f"Email sent successfully to {to_email} on attempt {attempt + 1}")
                return True
                
            except smtplib.SMTPConnectError as e:
                logger.error(f"Failed to connect to SMTP server {settings.smtp_host}:{settings.smtp_port}: {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying email send... (attempt {attempt + 2}/{retry_count})")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                return False
                
            except smtplib.SMTPServerDisconnected as e:
                logger.error(f"SMTP server disconnected unexpectedly: {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying email send... (attempt {attempt + 2}/{retry_count})")
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return False
                
            except Exception as e:
                logger.error(f"SMTP error sending to {to_email}: {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying email send... (attempt {attempt + 2}/{retry_count})")
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return False
        
        return False


# Global email service instance
email_service = EmailService()