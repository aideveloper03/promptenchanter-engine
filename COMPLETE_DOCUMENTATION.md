# PromptEnchanter - Complete Documentation

**Version**: 2.0.0  
**Last Updated**: October 7, 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Authentication & Authorization](#authentication--authorization)
8. [Email Verification](#email-verification)
9. [User Management](#user-management)
10. [Security](#security)
11. [Deployment](#deployment)
12. [Monitoring & Logging](#monitoring--logging)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices](#best-practices)

---

## Introduction

PromptEnchanter is an enterprise-grade AI service that enhances user prompts through:
- **AI-powered research** with internet access
- **Multiple prompt engineering methodologies** (BPE, BCOT, HCOT, ReAct, ToT)
- **Intelligent caching** for improved performance
- **Comprehensive user management** with API key authentication
- **Email verification** with OTP (optional)
- **Enterprise security** with encryption, firewall, and audit logging

### Key Capabilities

🎯 **AI API Proxying** - Seamlessly forwards enhanced requests to external AI APIs  
🧠 **Prompt Engineering** - Multiple reasoning methodologies for optimal AI responses  
🔍 **AI Deep Research** - Internet-powered research with multi-source synthesis  
⚡ **Batch Processing** - Efficient parallel or sequential prompt processing  
🔐 **Enterprise Security** - Comprehensive security with encryption and firewall  
💾 **Intelligent Caching** - Redis-based caching with fallback to memory

---

## Features

### Core Features

#### 1. Prompt Engineering Styles (r_type)

| Style | Code | Description |
|-------|------|-------------|
| **Basic Prompt Engineering** | `bpe` | Clear, structured responses with detailed planning |
| **Basic Chain of Thoughts** | `bcot` | Step-by-step reasoning process |
| **High Chain of Thoughts** | `hcot` | Advanced multi-angle analysis |
| **ReAct** | `react` | Reasoning + Action methodology (Observe, Think, Act, Reflect) |
| **Tree of Thoughts** | `tot` | Multiple thought branches with evaluation |

#### 2. AI Deep Research

- Automatic topic identification and research planning
- Multi-source web search and content extraction
- AI-powered content synthesis and classification
- Configurable research depth (basic, medium, high)
- Intelligent caching of research results (24-hour TTL)

#### 3. User Management

- **Registration & Authentication** - Secure user accounts with session management
- **API Key Management** - Unique API keys with regeneration capability
- **Credit System** - Conversation credits with automatic daily resets
- **Profile Management** - Complete user profile with customizable fields
- **Email Verification** - Optional OTP-based email verification
- **Account Deletion** - Soft delete with data archiving

#### 4. Admin Features

- **Admin Panel** - Full administrative control
- **Support Staff System** - Role-based support (new/support/advanced)
- **User Management** - Create, update, delete users
- **Security Logs** - Comprehensive audit trails
- **System Configuration** - Runtime configuration updates

#### 5. Security Features

- **Argon2id Password Hashing** - Industry-standard password security
- **IP Whitelisting** - Restrict access by IP address (optional)
- **Firewall** - Block malicious IPs automatically
- **Failed Attempt Tracking** - Account lockout after 5 failed attempts
- **Data Encryption** - Sensitive data encrypted at rest
- **Session Management** - Secure session tokens with expiration

---

## Architecture

### Technology Stack

- **Framework**: FastAPI (Python 3.8+)
- **Database**: MongoDB (primary) + SQLite (legacy support)
- **Cache**: Redis with memory fallback
- **Authentication**: JWT with Argon2id password hashing
- **Email**: SMTP with multiple provider support
- **Logging**: Structured logging with request tracing

### System Components

```
┌─────────────────────────────────────────────┐
│           FastAPI Application               │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │   API v1    │  │   Middleware Layer   │ │
│  │  Endpoints  │  │  - Authentication    │ │
│  │             │  │  - Rate Limiting     │ │
│  │             │  │  - Firewall          │ │
│  │             │  │  - Logging           │ │
│  └─────────────┘  └──────────────────────┘ │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Services   │  │    Security Layer    │ │
│  │  - Prompt   │  │  - Encryption        │ │
│  │  - Research │  │  - Password Manager  │ │
│  │  - Email    │  │  - Token Manager     │ │
│  │  - User     │  │  - IP Security       │ │
│  └─────────────┘  └──────────────────────┘ │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Database   │  │    Cache Layer       │ │
│  │  - MongoDB  │  │  - Redis             │ │
│  │  - SQLite   │  │  - Memory Fallback   │ │
│  └─────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────┘
            │                      │
            ▼                      ▼
    ┌──────────────┐      ┌──────────────┐
    │   External   │      │    SMTP      │
    │   AI API     │      │   Provider   │
    └──────────────┘      └──────────────┘
```

### Request Flow

1. **Client Request** → API Endpoint
2. **Firewall Check** → Block if IP blacklisted
3. **Authentication** → Validate API key or session token
4. **Rate Limiting** → Check request limits
5. **Authorization** → Verify permissions
6. **Business Logic** → Process request
7. **AI Enhancement** → Apply prompt engineering
8. **Research** (optional) → Conduct AI research
9. **Caching** → Check/store in cache
10. **AI API Call** → Forward to external AI
11. **Response** → Return enhanced result
12. **Logging** → Audit and analytics

---

## Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB (local or Atlas)
- Redis (optional, for caching)
- SMTP account (optional, for email verification)

### Quick Start

#### 1. Clone Repository

```bash
git clone <repository-url>
cd promptenchanter
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

#### 4. Initialize Database

```bash
# MongoDB will auto-initialize on first run
# Default admin user will be created automatically
```

#### 5. Run Application

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment (Recommended)

#### Quick Start with Docker

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test deployment
curl http://localhost:8000/health
```

#### Production Docker

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Configuration

### Environment Variables

Complete `.env` configuration:

```env
# ===== CORE API CONFIGURATION =====
API_KEY=pe-default-api-key-change-in-production
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=sk-your-wapi-key

# ===== SERVER CONFIGURATION =====
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# ===== SECURITY CONFIGURATION =====
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256

# ===== DATABASE CONFIGURATION =====
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=promptenchanter
USE_MONGODB=true
DATABASE_URL=sqlite+aiosqlite:///./data/promptenchanter2.db

# ===== REDIS CONFIGURATION =====
REDIS_URL=redis://localhost:6379/0

# ===== USER MANAGEMENT =====
USER_REGISTRATION_ENABLED=true
EMAIL_VERIFICATION_ENABLED=true

# ===== EMAIL CONFIGURATION =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=noreply@promptenchanter.com

# ===== SECURITY SETTINGS =====
IP_WHITELIST_ENABLED=false
FIREWALL_ENABLED=true
MAX_FAILED_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_HOURS=1

# ===== SESSION SETTINGS =====
SESSION_DURATION_HOURS=24
REFRESH_TOKEN_DURATION_DAYS=30

# ===== RATE LIMITING =====
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# ===== CACHE SETTINGS =====
CACHE_TTL_SECONDS=3600
RESEARCH_CACHE_TTL_SECONDS=86400

# ===== ADMIN CONFIGURATION =====
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=ChangeThisPassword123!
DEFAULT_ADMIN_EMAIL=admin@promptenchanter.com
```

### Configuration Reference

See [Configuration Guide](#configuration-guide) for detailed explanations of each variable.

---

## API Reference

### Base URL

```
http://localhost:8000/v1
```

### Authentication

All API requests require authentication via Bearer token:

```bash
Authorization: Bearer <api_key_or_session_token>
```

### Core Endpoints

#### 1. User Registration

```bash
POST /v1/users/register
Content-Type: application/json

{
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "user_type": "Personal"
}

# Response
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "507f1f77bcf86cd799439011",
  "username": "johndoe",
  "email": "john@example.com",
  "api_key": "pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y",
  "verification_required": true
}
```

#### 2. User Login

```bash
POST /v1/users/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!"
}

# Response
{
  "success": true,
  "session_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "username": "johndoe",
    "email": "john@example.com",
    "is_verified": false
  }
}
```

#### 3. Email Verification

```bash
# Send verification email
POST /v1/email/send-verification
Authorization: Bearer <session_token>

# Verify OTP
POST /v1/email/verify
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "otp_code": "123456"
}

# Check verification status
GET /v1/email/status
Authorization: Bearer <session_token>
```

#### 4. Get Profile

```bash
GET /v1/users/profile
Authorization: Bearer <session_token_or_api_key>

# Response
{
  "id": "507f1f77bcf86cd799439011",
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "is_verified": true,
  "credits": {"main": 10, "reset": 10},
  "level": "medium",
  "subscription_plan": "free"
}
```

#### 5. Chat Completion

```bash
POST /v1/prompt/completions
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "level": "medium",
  "messages": [
    {
      "role": "user",
      "content": "Explain quantum computing"
    }
  ],
  "r_type": "hcot",
  "ai_research": true,
  "research_depth": "high",
  "temperature": 0.7
}
```

#### 6. Batch Processing

```bash
POST /v1/batch/process
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "batch": [
    {
      "prompt": "Explain machine learning",
      "r_type": "bpe"
    },
    {
      "prompt": "Create a React component",
      "r_type": "react"
    }
  ],
  "level": "medium",
  "enable_research": true,
  "parallel": true
}
```

### Complete API Documentation

For complete API documentation with all endpoints, see:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

---

## Authentication & Authorization

### Authentication Methods

#### 1. API Key Authentication

**Use Case**: API access, long-lived authentication

```bash
Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y
```

**Features**:
- Permanent until regenerated
- Tied to user account
- Can be regenerated by user
- Suitable for programmatic access

#### 2. Session Token Authentication

**Use Case**: Web applications, short-lived sessions

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Features**:
- Expires after 24 hours (configurable)
- Refresh token for renewal
- Tied to IP and user agent (optional)
- Automatic session tracking

### Email Verification Behavior

**Important**: Profile access is **ALLOWED** without email verification

#### Without Verification

✅ Access profile  
✅ Update profile  
✅ View account details  
✅ Basic API usage  

#### Requires Verification (Optional, Configurable Per Endpoint)

⚠️ Sensitive operations (if configured)  
⚠️ Premium features (if configured)  
⚠️ High-value transactions (if configured)

### Authorization Levels

1. **User** - Standard user access
2. **Support Staff** - Support operations (new/support/advanced)
3. **Admin** - Full administrative access
4. **Super Admin** - System-level configuration

---

## Email Verification

### Overview

PromptEnchanter includes an optional email verification system that:
- Sends 6-digit OTP codes to users
- Validates email addresses
- Supports multiple SMTP providers
- Includes automatic retry logic
- Allows profile access without verification

### Setup

See **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** for comprehensive email setup instructions.

### Quick Setup (Gmail)

```env
EMAIL_VERIFICATION_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

### Verification Flow

1. User registers → Receives API key immediately
2. System sends OTP email (if configured)
3. User can access profile without verification
4. User verifies email when ready
5. Verification status updated in database

### Disable Email Verification

```env
EMAIL_VERIFICATION_ENABLED=false
```

Users will be automatically marked as verified.

---

## User Management

### User Lifecycle

```
Registration → Email Sent → Profile Access → Verification → Full Access
     ↓              ↓              ↓              ↓             ↓
  API Key      OTP Email    Unverified     OTP Submit    Verified
  Generated      Sent         Profile       Validated     Status
```

### User Attributes

```python
{
  "id": "507f1f77bcf86cd799439011",
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "user_type": "Personal",  # or "Business"
  "subscription_plan": "free",  # free, basic, pro, enterprise
  "credits": {"main": 10, "reset": 10},
  "limits": {"conversation_limit": 20, "reset": 20},
  "access_rtype": ["bpe", "tot", "bcot", "hcot", "react"],
  "level": "medium",  # low, medium, high, ultra
  "is_verified": true,
  "is_active": true,
  "last_login": "2025-10-07T10:30:00Z",
  "time_created": "2025-10-01T08:00:00Z"
}
```

### Credit System

- **Main Credits**: Current conversation credits
- **Reset Credits**: Daily reset amount
- **Auto Reset**: Automatic credit replenishment at midnight UTC
- **Deduction**: 1 credit per API call (configurable)

### User Operations

#### Update Profile

```bash
PUT /v1/users/profile
Authorization: Bearer <token>

{
  "name": "John Updated",
  "about_me": "AI enthusiast",
  "hobbies": "Machine learning, coding"
}
```

#### Change Email

```bash
PUT /v1/users/email
Authorization: Bearer <token>

{
  "new_email": "newemail@example.com",
  "current_password": "SecurePass123!"
}
```

#### Reset Password

```bash
PUT /v1/users/password
Authorization: Bearer <token>

{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

#### Delete Account

```bash
DELETE /v1/users/account
Authorization: Bearer <token>

{
  "password": "SecurePass123!",
  "reason": "No longer needed"
}
```

---

## Security

### Password Security

- **Algorithm**: Argon2id (memory-hard hashing)
- **Parameters**:
  - Time cost: 3 iterations
  - Memory cost: 64 MB
  - Parallelism: 1 thread
  - Salt length: 16 bytes
  - Hash length: 32 bytes

### Password Requirements

- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- No common passwords (validated against blacklist)

### Session Security

- **Session Duration**: 24 hours (configurable)
- **Refresh Token**: 30 days (configurable)
- **IP Binding**: Optional IP-based session validation
- **User Agent**: Stored for anomaly detection

### Data Encryption

- **Sensitive Data**: Encrypted using Fernet (AES-128)
- **API Keys**: Stored hashed in database
- **Passwords**: Argon2id hashed (never stored in plaintext)
- **Master Key**: Stored in `master.key` (chmod 600)

### Firewall & IP Protection

```python
# Automatic IP blocking
- Failed login attempts: 5 → 1 hour lockout
- Suspicious activity: Automatic blacklist
- Whitelist mode: Only allow specific IPs (optional)
```

### Security Logging

All security events are logged:
- Login attempts (success/failure)
- API key usage
- Password changes
- Account deletions
- Suspicious activity

---

## Deployment

### Development

```bash
python main.py
```

### Production (Uvicorn)

```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### Production (Gunicorn)

```bash
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker Production

```bash
# Build
docker build -t promptenchanter:latest .

# Run
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name promptenchanter \
  promptenchanter:latest

# With Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment-Specific Settings

#### Development
```env
DEBUG=true
LOG_LEVEL=DEBUG
EMAIL_VERIFICATION_ENABLED=false
```

#### Staging
```env
DEBUG=false
LOG_LEVEL=INFO
EMAIL_VERIFICATION_ENABLED=true
```

#### Production
```env
DEBUG=false
LOG_LEVEL=WARNING
EMAIL_VERIFICATION_ENABLED=true
FIREWALL_ENABLED=true
IP_WHITELIST_ENABLED=true
```

---

## Monitoring & Logging

### Structured Logging

All logs are structured JSON in production:

```json
{
  "timestamp": "2025-10-07T10:30:45.123Z",
  "level": "INFO",
  "request_id": "abc123-def456",
  "user_id": "507f1f77bcf86cd799439011",
  "message": "User login successful",
  "metadata": {
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (application errors)
- **CRITICAL**: Critical messages (system failures)

### Health Checks

```bash
# Basic health
GET /health

# Detailed health
GET /v1/monitoring/health

# System metrics
GET /v1/monitoring/metrics
```

### Metrics Tracking

- Request count and latency
- Error rates by endpoint
- User activity
- API usage statistics
- Credit consumption
- Cache hit/miss rates

---

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Failed

**Symptoms**:
```
Failed to connect to MongoDB: ServerSelectionTimeoutError
```

**Solutions**:
- Check MongoDB URL in `.env`
- Verify network connectivity
- Ensure MongoDB is running
- Check firewall rules
- Verify credentials

#### 2. Redis Connection Failed

**Symptoms**:
```
Failed to connect to Redis. Using memory cache fallback.
```

**Solutions**:
- Check Redis URL in `.env`
- Verify Redis is running: `redis-cli ping`
- Check port 6379 is accessible
- **Note**: System works with memory fallback

#### 3. Email Not Sending

**Symptoms**:
- No email received
- SMTP errors in logs

**Solutions**:
- See [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)
- Check SMTP credentials
- Verify email provider settings
- Check spam folder
- Enable DEBUG mode for detailed SMTP logs

#### 4. Authentication Failed

**Symptoms**:
```
401: Invalid or expired session token
```

**Solutions**:
- Check Authorization header format
- Verify token hasn't expired
- Use correct token type (API key vs session)
- Regenerate API key if needed

#### 5. Rate Limit Exceeded

**Symptoms**:
```
429: Too many requests
```

**Solutions**:
- Wait for rate limit reset (1 minute)
- Reduce request frequency
- Increase rate limits in `.env`
- Use admin/support account (bypasses limits)

---

## Best Practices

### Development

1. **Use Environment Variables**
   - Never hardcode credentials
   - Use `.env.example` as template
   - Keep `.env` out of version control

2. **Enable Debug Mode**
   ```env
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

3. **Test Email Locally**
   - Use Gmail with app password
   - Or disable email verification during development

4. **Use Memory Cache**
   - Redis optional in development
   - Fallback to memory cache works fine

### Production

1. **Security First**
   - Change all default passwords
   - Use strong `SECRET_KEY`
   - Enable email verification
   - Enable firewall
   - Use IP whitelisting if applicable

2. **Database Optimization**
   - Use MongoDB Atlas (managed)
   - Enable connection pooling
   - Set appropriate timeouts
   - Use indexes (auto-created)

3. **Caching Strategy**
   - Use Redis in production
   - Configure appropriate TTLs
   - Monitor cache hit rates
   - Implement cache warming if needed

4. **Monitoring**
   - Set up log aggregation (ELK, Datadog)
   - Monitor error rates
   - Track performance metrics
   - Set up alerts for critical errors

5. **Email Delivery**
   - Use dedicated email service (SendGrid, SES)
   - Configure SPF, DKIM, DMARC
   - Monitor delivery rates
   - Handle bounces gracefully

### API Usage

1. **Authentication**
   - Use API keys for programmatic access
   - Use session tokens for web applications
   - Implement token refresh logic
   - Handle 401 errors gracefully

2. **Rate Limiting**
   - Implement exponential backoff
   - Cache responses when possible
   - Use batch endpoints for multiple requests
   - Monitor rate limit headers

3. **Error Handling**
   - Handle all HTTP error codes
   - Implement retry logic for 5xx errors
   - Log errors for debugging
   - Show user-friendly error messages

---

## Additional Resources

### Documentation Files

- **[README.md](README.md)** - Quick start guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** - Email configuration guide
- **[COMPREHENSIVE_ANALYSIS.md](COMPREHENSIVE_ANALYSIS.md)** - Architecture analysis
- **[IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md)** - Implementation details

### API Endpoints

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Support

For additional help:
1. Check logs: `tail -f logs/promptenchanter.log`
2. Enable debug mode: `DEBUG=true`
3. Review documentation files
4. Check GitHub issues
5. Contact support team

---

**Last Updated**: October 7, 2025  
**Version**: 2.0.0  
**License**: MIT
