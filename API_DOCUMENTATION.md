# PromptEnchanter API Documentation

**Version:** 1.0.0  
**Base URL:** `https://your-domain.com/v1`  
**Last Updated:** 2025-10-05

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [User Management Endpoints](#user-management-endpoints)
6. [Email Verification Endpoints](#email-verification-endpoints)
7. [Chat/Prompt Enhancement Endpoints](#chatprompt-enhancement-endpoints)
8. [Batch Processing Endpoints](#batch-processing-endpoints)
9. [Admin Panel Endpoints](#admin-panel-endpoints)
10. [Support Staff Endpoints](#support-staff-endpoints)
11. [Monitoring Endpoints](#monitoring-endpoints)

---

## Overview

PromptEnchanter is an enterprise-grade AI prompt enhancement service that provides:

- **Prompt Engineering Styles**: Multiple prompt engineering methodologies (BPE, BCOT, HCOT, ReAct, ToT)
- **AI Deep Research**: Automatic research enhancement with internet access
- **Batch Processing**: Process multiple prompts efficiently
- **User Management**: Complete user authentication and management system
- **Admin Controls**: System management and monitoring

---

## Authentication

PromptEnchanter uses Bearer token authentication for all protected endpoints.

### Authentication Types

1. **API Key Authentication** (Recommended for API access)
   ```
   Authorization: Bearer pe-your-api-key-here
   ```

2. **Session Token Authentication** (For web applications)
   ```
   Authorization: Bearer session-token-here
   ```

### Getting an API Key

1. Register a new user account
2. Verify your email (if email verification is enabled)
3. Login to get a session token
4. Use the session token to retrieve your API key from `/v1/users/api-key`

### Email Verification

If email verification is enabled (`EMAIL_VERIFICATION_ENABLED=true`):
- New users must verify their email before accessing API keys
- Unverified users can login but cannot access protected resources
- Admins can bypass email verification requirements

---

## Error Handling

### Standard Error Response

All errors follow this format:

```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Detailed error 1", "Detailed error 2"],
  "details": {
    "request_id": "unique-request-id",
    "additional_context": "value"
  }
}
```

### Common HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 423 | Locked | Account is locked |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error occurred |

---

## Rate Limiting

### Default Limits

- **Standard Endpoints**: 100 requests/minute with burst support
- **Batch Endpoints**: 25 requests/minute with reduced burst
- **Admin Endpoints**: Higher limits for authenticated admins

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1633024800
```

### Rate Limit Exceeded Response

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}
```

---

## User Management Endpoints

### Register New User

**Endpoint:** `POST /v1/users/register`  
**Authentication:** None (Public)  
**Rate Limit:** 10 requests/hour per IP

#### Request Body

```json
{
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "user_type": "Personal",
  "about_me": "Software developer",
  "hobbies": "Coding, Reading"
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Unique username (3-50 chars, alphanumeric with - and _) |
| name | string | Yes | Full name (2-100 chars) |
| email | string | Yes | Valid email address |
| password | string | Yes | Password (min 8 chars, 1 number required) |
| user_type | string | No | "Personal" or "Business" (default: "Personal") |
| about_me | string | No | About me section (max 1000 chars) |
| hobbies | string | No | User hobbies (max 500 chars) |

#### Response (201 Created)

```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "507f1f77bcf86cd799439011",
  "username": "johndoe",
  "email": "john@example.com",
  "api_key": "pe-xxxxxxxxxxxxxxxxxxxxxx",
  "verification_required": true
}
```

#### Possible Errors

- `400 Bad Request`: Invalid input data
- `409 Conflict`: Username or email already exists
- `500 Internal Server Error`: Server error

---

### User Login

**Endpoint:** `POST /v1/users/login`  
**Authentication:** None (Public)  
**Rate Limit:** 20 requests/hour per IP

#### Request Body

```json
{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": "507f1f77bcf86cd799439011",
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
    "expires_at": "2025-10-06T10:00:00Z",
    "refresh_expires_at": "2025-11-05T10:00:00Z"
  }
}
```

#### Possible Errors

- `401 Unauthorized`: Invalid credentials
- `423 Locked`: Account locked due to failed attempts

---

### User Logout

**Endpoint:** `POST /v1/users/logout`  
**Authentication:** Session token required  
**Rate Limit:** 100 requests/minute

#### Headers

```
Authorization: Bearer <session_token>
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### Get User Profile

**Endpoint:** `GET /v1/users/profile`  
**Authentication:** Session token required  
**Rate Limit:** 100 requests/minute

#### Headers

```
Authorization: Bearer <session_token>
```

#### Response (200 OK)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "about_me": "Software developer",
  "hobbies": "Coding, Reading",
  "user_type": "Personal",
  "time_created": "2025-10-05T10:00:00Z",
  "subscription_plan": "free",
  "credits": {
    "main": 10,
    "reset": 10
  },
  "limits": {
    "conversation_limit": 20,
    "reset": 20
  },
  "access_rtype": ["bpe", "tot", "bcot", "hcot", "react"],
  "level": "medium",
  "additional_notes": "",
  "is_verified": false,
  "last_login": "2025-10-05T09:30:00Z",
  "last_activity": "2025-10-05T10:00:00Z"
}
```

---

### Update User Profile

**Endpoint:** `PUT /v1/users/profile`  
**Authentication:** Session token required  
**Rate Limit:** 100 requests/minute

#### Request Body

```json
{
  "name": "John Updated Doe",
  "about_me": "Updated bio",
  "hobbies": "Updated hobbies"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Profile updated successfully"
}
```

---

### Get API Key

**Endpoint:** `GET /v1/users/api-key`  
**Authentication:** Session token required  
**Email Verification:** Required (if enabled)  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "success": true,
  "message": "API key retrieved successfully",
  "api_key": "pe-xxxxxxxxxxxxxxxxxxxxxx"
}
```

#### Possible Errors

- `403 Forbidden`: Email verification required

---

### Regenerate API Key

**Endpoint:** `POST /v1/users/api-key/regenerate`  
**Authentication:** Session token required  
**Email Verification:** Required (if enabled)  
**Rate Limit:** 10 requests/hour

#### Response (200 OK)

```json
{
  "success": true,
  "message": "API key regenerated successfully",
  "api_key": "pe-new-api-key-xxxxxxxxxx"
}
```

---

### Update Email

**Endpoint:** `PUT /v1/users/email`  
**Authentication:** Session token required  
**Rate Limit:** 10 requests/hour

#### Request Body

```json
{
  "new_email": "newemail@example.com",
  "current_password": "SecurePass123!"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Email updated successfully. Please verify your new email address."
}
```

---

### Reset Password

**Endpoint:** `PUT /v1/users/password`  
**Authentication:** Session token required  
**Rate Limit:** 10 requests/hour

#### Request Body

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePass123!"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

---

### Delete Account

**Endpoint:** `DELETE /v1/users/account`  
**Authentication:** Session token required  
**Rate Limit:** 5 requests/day

#### Request Body

```json
{
  "password": "SecurePass123!",
  "reason": "No longer needed"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Account deleted successfully"
}
```

---

## Email Verification Endpoints

### Send Verification Email

**Endpoint:** `POST /v1/email/send-verification`  
**Authentication:** Session token required  
**Rate Limit:** 3 requests/day per user

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Verification email sent successfully",
  "expires_at": "2025-10-06T10:00:00Z"
}
```

---

### Verify Email with OTP

**Endpoint:** `POST /v1/email/verify`  
**Authentication:** Session token required  
**Rate Limit:** 10 requests/hour

#### Request Body

```json
{
  "otp_code": "123456"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

#### Possible Errors

- `400 Bad Request`: Invalid OTP format or expired OTP
- `429 Too Many Requests`: Too many verification attempts

---

### Resend Verification Email

**Endpoint:** `POST /v1/email/resend`  
**Authentication:** Session token required  
**Rate Limit:** 3 requests/day per user

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Verification email sent successfully",
  "expires_at": "2025-10-06T10:00:00Z"
}
```

---

### Get Verification Status

**Endpoint:** `GET /v1/email/status`  
**Authentication:** Session token required  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "success": true,
  "is_verified": false,
  "email": "john@example.com",
  "verification_enabled": true,
  "verification_required_for_api": true
}
```

---

## Chat/Prompt Enhancement Endpoints

### Enhance Prompt (Single)

**Endpoint:** `POST /v1/prompt/enhance`  
**Authentication:** API key required  
**Email Verification:** Required (if enabled)  
**Rate Limit:** 100 requests/minute

#### Request Body

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Explain quantum computing"
    }
  ],
  "model": "gpt-4",
  "r_type": "bpe",
  "research": true,
  "use_cache": true
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| messages | array | Yes | Array of message objects with role and content |
| model | string | No | AI model to use (default: system configured) |
| r_type | string | No | Prompt engineering type: "bpe", "tot", "bcot", "hcot", "react" |
| research | boolean | No | Enable AI research (default: true) |
| use_cache | boolean | No | Use cached responses (default: true) |

#### Response (200 OK)

```json
{
  "success": true,
  "enhanced_prompt": "...",
  "response": {
    "content": "Quantum computing is...",
    "model": "gpt-4",
    "tokens_used": 1500,
    "finish_reason": "stop"
  },
  "research_data": {
    "sources": [...],
    "summary": "..."
  },
  "cached": false,
  "processing_time_ms": 3456
}
```

---

## Batch Processing Endpoints

### Submit Batch Request

**Endpoint:** `POST /v1/batch/submit`  
**Authentication:** API key required  
**Rate Limit:** 25 requests/minute

#### Request Body

```json
{
  "tasks": [
    {
      "task_id": "task-1",
      "messages": [...],
      "r_type": "bpe"
    },
    {
      "task_id": "task-2",
      "messages": [...],
      "r_type": "react"
    }
  ],
  "execution_mode": "parallel",
  "max_parallel_tasks": 5
}
```

#### Response (202 Accepted)

```json
{
  "success": true,
  "batch_id": "batch-xxxxx",
  "total_tasks": 2,
  "status": "processing"
}
```

---

### Get Batch Status

**Endpoint:** `GET /v1/batch/{batch_id}/status`  
**Authentication:** API key required  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "batch_id": "batch-xxxxx",
  "status": "completed",
  "total_tasks": 2,
  "completed_tasks": 2,
  "failed_tasks": 0,
  "progress_percentage": 100.0
}
```

---

## Admin Panel Endpoints

### Admin Login

**Endpoint:** `POST /v1/admin-panel/login`  
**Authentication:** None (Public)  
**Rate Limit:** 10 requests/hour per IP

#### Request Body

```json
{
  "username": "admin",
  "password": "AdminPass123!"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Admin login successful",
  "admin": {
    "id": "507f1f77bcf86cd799439011",
    "username": "admin",
    "name": "System Administrator",
    "email": "admin@example.com",
    "is_super_admin": true,
    "permissions": ["all"],
    "last_login": null
  },
  "session": {
    "session_token": "...",
    "refresh_token": "...",
    "expires_at": "...",
    "refresh_expires_at": "..."
  }
}
```

---

### Get Users List (Admin)

**Endpoint:** `GET /v1/admin-panel/users`  
**Authentication:** Admin session token required  
**Rate Limit:** 100 requests/minute

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| page | integer | Page number (default: 1) |
| page_size | integer | Items per page (default: 50, max: 100) |
| search | string | Search by username, name, or email |
| user_type | string | Filter by user type |
| is_active | boolean | Filter by active status |
| is_verified | boolean | Filter by verification status |

#### Response (200 OK)

```json
{
  "users": [
    {
      "id": "...",
      "username": "...",
      "name": "...",
      "email": "...",
      ...
    }
  ],
  "total_count": 150,
  "page": 1,
  "page_size": 50
}
```

---

### Update User (Admin)

**Endpoint:** `PUT /v1/admin-panel/users/{user_id}`  
**Authentication:** Admin session token required  
**Rate Limit:** 100 requests/minute

#### Request Body

```json
{
  "name": "Updated Name",
  "subscription_plan": "premium",
  "credits": {
    "main": 100,
    "reset": 100
  },
  "is_active": true,
  "is_verified": true
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "User updated successfully"
}
```

---

### Delete User (Admin)

**Endpoint:** `DELETE /v1/admin-panel/users/{user_id}`  
**Authentication:** Admin session token required  
**Rate Limit:** 50 requests/hour

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| reason | string | Deletion reason |

#### Response (200 OK)

```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

## Support Staff Endpoints

### Support Staff Login

**Endpoint:** `POST /v1/support/login`  
**Authentication:** None (Public)  
**Rate Limit:** 10 requests/hour per IP

#### Request Body

```json
{
  "username": "support_user",
  "password": "SupportPass123!"
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Support staff login successful",
  "staff": {
    "id": "...",
    "username": "support_user",
    "name": "Support Staff",
    "email": "support@example.com",
    "staff_level": "support",
    "is_active": true,
    "time_created": "...",
    "created_by": "admin",
    "last_login": null
  },
  "session": {...}
}
```

---

### View User Details (Support)

**Endpoint:** `GET /v1/support/users/{user_id}`  
**Authentication:** Support staff session token required  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "user": {
    "id": "...",
    "username": "...",
    "name": "...",
    "email": "...",
    ...
  }
}
```

---

## Monitoring Endpoints

### Health Check

**Endpoint:** `GET /health`  
**Authentication:** None (Public)  
**Rate Limit:** None

#### Response (200 OK)

```json
{
  "status": "healthy",
  "service": "PromptEnchanter",
  "version": "1.0.0"
}
```

---

### System Status (Admin)

**Endpoint:** `GET /v1/monitoring/system-status`  
**Authentication:** Admin session token required  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "status": "healthy",
  "database_connected": true,
  "redis_connected": true,
  "total_users": 1500,
  "active_sessions": 250,
  "system_load": {
    "cpu": 45.2,
    "memory": 62.5,
    "disk": 35.0
  },
  "uptime_seconds": 86400.5
}
```

---

### User Statistics (Admin)

**Endpoint:** `GET /v1/monitoring/user-statistics`  
**Authentication:** Admin session token required  
**Rate Limit:** 100 requests/minute

#### Response (200 OK)

```json
{
  "total_users": 1500,
  "active_users": 1200,
  "verified_users": 1100,
  "users_by_type": {
    "Personal": 1300,
    "Business": 200
  },
  "users_by_plan": {
    "free": 1400,
    "premium": 100
  },
  "new_users_today": 15,
  "new_users_this_week": 75,
  "new_users_this_month": 250
}
```

---

## Best Practices

### Security

1. **Never expose your API key** in client-side code or public repositories
2. **Rotate API keys regularly** for security
3. **Use HTTPS** for all API requests in production
4. **Implement rate limiting** on your side to avoid hitting limits
5. **Store credentials securely** using environment variables or secure vaults

### Performance

1. **Use caching** when possible to reduce API calls
2. **Batch requests** when processing multiple prompts
3. **Monitor your usage** to optimize costs and performance
4. **Handle errors gracefully** with proper retry logic

### Error Handling

1. **Always check the `success` field** in responses
2. **Log errors** for debugging and monitoring
3. **Implement exponential backoff** for rate limit errors
4. **Validate inputs** before sending requests

---

## Support

For additional support:

- **Email**: support@promptenchanter.com
- **Documentation**: https://docs.promptenchanter.com
- **Status Page**: https://status.promptenchanter.com

---

**Last Updated**: 2025-10-05  
**API Version**: 1.0.0
