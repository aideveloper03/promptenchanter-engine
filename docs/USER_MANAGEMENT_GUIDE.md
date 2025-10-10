# PromptEnchanter User Management System

## Overview

PromptEnchanter now includes a comprehensive user management system with advanced security features, role-based access control, and high-performance message logging. This system provides:

- **User Registration & Authentication**: Secure user accounts with API key management
- **Admin Panel**: Full administrative control over users and system
- **Support Staff System**: Role-based support staff with limited permissions
- **Security Features**: IP whitelisting, firewall, encryption, and audit logging
- **Message Logging**: High-performance batch logging of all conversations
- **Credit Management**: Automated daily credit resets and usage tracking

## Table of Contents

1. [User Registration & Authentication](#user-registration--authentication)
2. [API Authentication](#api-authentication)
3. [Admin Panel](#admin-panel)
4. [Support Staff System](#support-staff-system)
5. [Security Features](#security-features)
6. [Message Logging](#message-logging)
7. [Configuration](#configuration)
8. [API Endpoints](#api-endpoints)

## User Registration & Authentication

### User Registration

Users can register for an account through the `/v1/users/register` endpoint.

**Required Information:**
- Username (3-50 characters, alphanumeric with hyphens/underscores)
- Full name (2-100 characters)
- Email address (valid format)
- Password (minimum 8 characters, at least 1 number, 1 uppercase, 1 lowercase)
- User type: "Personal" or "Business" (optional, defaults to "Personal")
- About me and hobbies (optional)

**Example Request:**
```bash
curl -X POST "https://api.promptenchanter.net/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "user_type": "Personal",
    "about_me": "AI enthusiast and developer",
    "hobbies": "Programming, reading, hiking"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "api_key": "pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y",
  "verification_required": true
}
```

### User Login

Users can login through the `/v1/users/login` endpoint to create a session.

**Example Request:**
```bash
curl -X POST "https://api.promptenchanter.net/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "johndoe",
    "name": "John Doe",
    "email": "john@example.com",
    "user_type": "Personal",
    "subscription_plan": "free",
    "is_verified": false
  },
  "session": {
    "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2024-01-15T12:00:00Z",
    "refresh_expires_at": "2024-02-14T12:00:00Z"
  }
}
```

### User Profile Management

Users can view and update their profile information:

```bash
# Get profile
curl "https://api.promptenchanter.net/v1/users/profile" \
  -H "Authorization: Bearer <session_token>"

# Update profile
curl -X PUT "https://api.promptenchanter.net/v1/users/profile" \
  -H "Authorization: Bearer <session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "about_me": "Updated bio",
    "hobbies": "AI, Machine Learning"
  }'
```

### API Key Management

```bash
# Get API key (encrypted)
curl "https://api.promptenchanter.net/v1/users/api-key" \
  -H "Authorization: Bearer <session_token>"

# Regenerate API key
curl -X POST "https://api.promptenchanter.net/v1/users/api-key/regenerate" \
  -H "Authorization: Bearer <session_token>"
```

## API Authentication

All API endpoints now require authentication using API keys:

```bash
curl "https://api.promptenchanter.net/v1/prompt/completions" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "medium",
    "messages": [{"role": "user", "content": "Hello"}],
    "r_type": "bpe"
  }'
```

### Credit System

Each API request consumes 1 conversation credit. Users have:
- **Main Credits**: Current available credits
- **Reset Credits**: Amount to reset to daily
- **Conversation Limit**: Current available credits (decremented on use)

When conversation_limit reaches 0, users receive a 429 error:

```json
{
  "message": "Insufficient conversation credits",
  "error_code": "CREDITS_EXHAUSTED",
  "limits": {
    "conversation_limit": 0,
    "reset": 10
  }
}
```

## Admin Panel

### Admin Creation

Create the first admin using the provided script:

```bash
python scripts/create_admin.py
```

### Admin Login

```bash
curl -X POST "https://api.promptenchanter.net/v1/admin-panel/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "AdminPass123"
  }'
```

### Admin Operations

**User Management:**
```bash
# List users
curl "https://api.promptenchanter.net/v1/admin-panel/users?page=1&page_size=50" \
  -H "Authorization: Bearer <admin_session_token>"

# Get user details
curl "https://api.promptenchanter.net/v1/admin-panel/users/1" \
  -H "Authorization: Bearer <admin_session_token>"

# Update user
curl -X PUT "https://api.promptenchanter.net/v1/admin-panel/users/1" \
  -H "Authorization: Bearer <admin_session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_plan": "premium",
    "credits": {"main": 100, "reset": 100},
    "limits": {"conversation_limit": 100, "reset": 100}
  }'

# Delete user (super admin only)
curl -X DELETE "https://api.promptenchanter.net/v1/admin-panel/users/1?reason=Policy violation" \
  -H "Authorization: Bearer <admin_session_token>"
```

**System Statistics:**
```bash
curl "https://api.promptenchanter.net/v1/admin-panel/statistics" \
  -H "Authorization: Bearer <admin_session_token>"
```

**Security Logs:**
```bash
curl "https://api.promptenchanter.net/v1/admin-panel/security-logs?page=1&severity=warning" \
  -H "Authorization: Bearer <admin_session_token>"
```

## Support Staff System

### Staff Levels

1. **New**: Read-only access to user information
2. **Support**: Can update email, password, credits, and subscription plans
3. **Advanced**: Can update most user fields, view messages, manage API keys

### Creating Support Staff

```bash
curl -X POST "https://api.promptenchanter.net/v1/support/create" \
  -H "Authorization: Bearer <admin_session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "support1",
    "name": "Support Staff 1",
    "email": "support1@company.com",
    "password": "SupportPass123",
    "staff_level": "support"
  }'
```

### Support Staff Login

```bash
curl -X POST "https://api.promptenchanter.net/v1/support/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "support1",
    "password": "SupportPass123"
  }'
```

### Support Operations

```bash
# View users (limited by staff level)
curl "https://api.promptenchanter.net/v1/support/users" \
  -H "Authorization: Bearer <support_session_token>"

# Update user credits (support level and above)
curl -X PUT "https://api.promptenchanter.net/v1/support/users/1/credits" \
  -H "Authorization: Bearer <support_session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "credits": {"main": 50, "reset": 50},
    "limits": {"conversation_limit": 50, "reset": 50}
  }'

# Reset user password (support level and above)
curl -X POST "https://api.promptenchanter.net/v1/support/users/1/reset-password" \
  -H "Authorization: Bearer <support_session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "NewSecurePass123"
  }'
```

## Security Features

### IP Whitelisting

Enable IP whitelisting in configuration:

```env
IP_WHITELIST_ENABLED=true
```

Add IPs through admin panel:

```bash
curl -X POST "https://api.promptenchanter.net/v1/admin-panel/ip-whitelist" \
  -H "Authorization: Bearer <admin_session_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "description": "Office network",
    "expires_at": "2024-12-31T23:59:59Z"
  }'
```

### Firewall Features

- **Rate Limiting**: 60 requests per minute per IP
- **Failed Attempt Tracking**: Temporary IP blocks after 5 failed attempts
- **Automatic Blocking**: 15-minute blocks for suspicious activity

### Encryption

- **Data Encryption**: Sensitive data encrypted at rest
- **API Key Encryption**: API keys encrypted when transmitted
- **Password Hashing**: bcrypt with salt for password security

## Message Logging

### High-Performance Logging

The system logs all API conversations with:
- **Batch Processing**: Messages queued and written in batches
- **Memory Management**: Automatic overflow protection
- **Concurrent Safety**: Thread-safe operations

### Log Structure

```json
{
  "id": 1,
  "user_id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "model": "gpt-4o",
  "messages": {
    "request": [
      {"role": "user", "content": "Hello"}
    ],
    "response": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    }
  },
  "research_enabled": false,
  "r_type": "bpe",
  "tokens_used": 25,
  "processing_time_ms": 1500,
  "ip_address": "192.168.1.100",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Accessing Logs

```bash
# Get user message logs (admin only)
curl "https://api.promptenchanter.net/v1/admin-panel/message-logs/1?page=1" \
  -H "Authorization: Bearer <admin_session_token>"
```

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./promptenchanter.db

# User Management
USER_REGISTRATION_ENABLED=true
EMAIL_VERIFICATION_ENABLED=false
DEFAULT_USER_CREDITS={"main": 5, "reset": 5}
DEFAULT_USER_LIMITS={"conversation_limit": 10, "reset": 10}

# Security
IP_WHITELIST_ENABLED=false
FIREWALL_ENABLED=true
MAX_FAILED_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_HOURS=1

# Sessions
SESSION_DURATION_HOURS=24
REFRESH_TOKEN_DURATION_DAYS=30
ADMIN_SESSION_DURATION_HOURS=24
SUPPORT_SESSION_DURATION_HOURS=12

# Message Logging
MESSAGE_LOGGING_ENABLED=true
MESSAGE_BATCH_SIZE=50
MESSAGE_FLUSH_INTERVAL_SECONDS=600
MESSAGE_MAX_QUEUE_SIZE=1000

# Credit Reset
AUTO_CREDIT_RESET_ENABLED=true
DAILY_USAGE_RESET_HOUR=0

# Email (for future features)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@promptenchanter.com
```

## API Endpoints

### User Management
- `POST /v1/users/register` - Register new user
- `POST /v1/users/login` - User login
- `POST /v1/users/refresh` - Refresh session
- `POST /v1/users/logout` - User logout
- `GET /v1/users/profile` - Get user profile
- `PUT /v1/users/profile` - Update user profile
- `GET /v1/users/api-key` - Get API key (encrypted)
- `POST /v1/users/api-key/regenerate` - Regenerate API key
- `PUT /v1/users/email` - Update email
- `PUT /v1/users/password` - Reset password
- `DELETE /v1/users/account` - Delete account

### Admin Panel
- `POST /v1/admin-panel/login` - Admin login
- `POST /v1/admin-panel/create-admin` - Create admin (super admin only)
- `GET /v1/admin-panel/users` - List users
- `GET /v1/admin-panel/users/{id}` - Get user details
- `PUT /v1/admin-panel/users/{id}` - Update user
- `DELETE /v1/admin-panel/users/{id}` - Delete user (super admin only)
- `GET /v1/admin-panel/statistics` - System statistics
- `GET /v1/admin-panel/security-logs` - Security logs
- `GET /v1/admin-panel/message-logs/{user_id}` - User message logs
- `GET /v1/admin-panel/health` - System health

### Support Staff
- `POST /v1/support/login` - Support staff login
- `POST /v1/support/create` - Create support staff (admin only)
- `GET /v1/support/profile` - Get staff profile
- `GET /v1/support/permissions` - Get staff permissions
- `GET /v1/support/users` - List users (limited view)
- `GET /v1/support/users/{id}` - Get user details (limited)
- `PUT /v1/support/users/{id}` - Update user (limited)
- `POST /v1/support/users/{id}/reset-password` - Reset user password
- `PUT /v1/support/users/{id}/credits` - Update user credits
- `PUT /v1/support/users/{id}/plan` - Update subscription plan

### Enhanced API Endpoints
- `POST /v1/prompt/completions` - Chat completion (requires authentication)
- `POST /v1/batch/process` - Batch processing (requires authentication)

## Error Handling

### Common Error Codes

- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid credentials/token)
- `403` - Forbidden (insufficient permissions)
- `409` - Conflict (username/email already exists)
- `423` - Locked (account temporarily locked)
- `429` - Too Many Requests (rate limit or credit exhaustion)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Specific error 1", "Specific error 2"],
  "details": {
    "request_id": "req_123456",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

## Best Practices

### Security
1. Use strong passwords for all accounts
2. Regularly rotate API keys
3. Enable IP whitelisting for production
4. Monitor security logs regularly
5. Use HTTPS in production

### Performance
1. Implement proper caching strategies
2. Monitor database performance
3. Use connection pooling
4. Optimize batch sizes for your load

### Monitoring
1. Set up log aggregation
2. Monitor API usage patterns
3. Track error rates
4. Monitor system resources

## Troubleshooting

### Common Issues

**Database Connection Errors:**
- Check DATABASE_URL configuration
- Ensure database file permissions
- Verify SQLite installation

**Authentication Failures:**
- Check API key format (must start with "pe-")
- Verify user account is active
- Check for account lockouts

**Credit Exhaustion:**
- Check user's conversation_limit
- Verify credit reset schedule
- Monitor daily usage patterns

**Performance Issues:**
- Check message queue size
- Monitor batch processing intervals
- Verify Redis connection

For additional support, check the logs at `/var/log/promptenchanter/` or contact your system administrator.