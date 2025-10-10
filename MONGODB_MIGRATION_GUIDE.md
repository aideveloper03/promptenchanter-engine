# MongoDB Migration Guide for PromptEnchanter

This guide explains the MongoDB migration and new features implemented in PromptEnchanter.

## 🚀 What's New

### ✅ MongoDB Integration
- **Primary Database**: MongoDB Atlas (cloud-hosted)
- **Fallback Support**: SQLite for development/testing
- **Automatic Collection Creation**: Collections and indexes are created on startup
- **Connection Management**: Robust connection handling with health checks

### ✅ Email Verification System
- **OTP-based Verification**: 6-digit OTP codes sent via email
- **Rate Limiting**: 3 verification emails per day per user
- **Configurable Expiry**: 24-hour default expiry for OTP codes
- **API Access Control**: Email verification required for API key access (when enabled)

### ✅ Enhanced User Management
- **MongoDB-native Operations**: All user operations use MongoDB
- **Improved Security**: Enhanced password policies and account locking
- **Session Management**: Robust session handling with MongoDB storage
- **Profile Management**: Complete user profile management system

### ✅ Admin & Support Systems
- **MongoDB Admin Service**: Complete admin management with MongoDB
- **Support Staff Management**: Support staff creation and management
- **Security Logging**: All security events logged to MongoDB

## 🔧 Configuration

### Environment Variables

The following environment variables have been added/updated:

```bash
# MongoDB Configuration
MONGODB_URL=mongodb+srv://your-connection-string
MONGODB_DATABASE=promptenchanter
USE_MONGODB=true

# Email Verification
EMAIL_VERIFICATION_ENABLED=true
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS=24
EMAIL_VERIFICATION_RESEND_LIMIT_PER_DAY=3
EMAIL_VERIFICATION_OTP_LENGTH=6

# SMTP Configuration (for email verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=noreply@promptenchanter.com
```

### WAPI Configuration

The system now uses the specified WAPI configuration:

```bash
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=sk-Xf6CNfK8A4bCmoRAE8pBRCKyEJrJKigjlVlqCtf07AZmpije
```

## 📋 API Endpoints

### New MongoDB-based Endpoints

#### User Management (`/v1/users/`)
- `POST /register` - Register new user with optional email verification
- `POST /login` - User authentication with session creation
- `POST /logout` - Session invalidation
- `GET /profile` - Get user profile
- `PUT /profile` - Update user profile
- `GET /api-key` - Get API key (requires email verification if enabled)
- `POST /api-key/regenerate` - Regenerate API key
- `PUT /email` - Update email address
- `PUT /password` - Change password
- `DELETE /account` - Delete account with data archiving

#### Email Verification (`/v1/email/`)
- `POST /send-verification` - Send verification email
- `POST /verify` - Verify email with OTP
- `POST /resend` - Resend verification email (rate limited)
- `GET /status` - Get verification status

#### Chat Completions (`/v1/prompt/`)
- `POST /completions` - Enhanced chat completions with MongoDB user management

### Legacy SQLite Endpoints

Legacy endpoints are still available with `-legacy` suffix:
- `/v1/users-legacy/` - SQLite-based user management
- `/v1/prompt-legacy/` - SQLite-based chat completions

## 🏗️ Database Schema

### MongoDB Collections

#### Users Collection
```javascript
{
  _id: ObjectId,
  username: String,
  name: String,
  email: String,
  password_hash: String,
  about_me: String,
  hobbies: String,
  user_type: String,
  time_created: Date,
  subscription_plan: String,
  credits: Object,
  limits: Object,
  access_rtype: Array,
  level: String,
  additional_notes: String,
  api_key: String,
  is_active: Boolean,
  is_verified: Boolean,
  email_verification_token: String,
  password_reset_token: String,
  password_reset_expires: Date,
  last_login: Date,
  failed_login_attempts: Number,
  locked_until: Date,
  created_at: Date,
  updated_at: Date,
  last_activity: Date
}
```

#### Email Verification Collection
```javascript
{
  _id: ObjectId,
  user_id: String,
  email: String,
  otp_code: String,
  expires_at: Date,
  created_at: Date,
  attempts: Number,
  verified: Boolean,
  resend_count: Number,
  last_resend: Date
}
```

#### User Sessions Collection
```javascript
{
  _id: ObjectId,
  user_id: String,
  session_token: String,
  refresh_token: String,
  expires_at: Date,
  refresh_expires_at: Date,
  ip_address: String,
  user_agent: String,
  is_active: Boolean,
  created_at: Date,
  last_used: Date
}
```

## 🚦 Email Verification Flow

### 1. User Registration
```bash
POST /v1/users/register
{
  "username": "testuser",
  "name": "Test User",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "user_type": "Personal"
}
```

Response includes `verification_required: true` if email verification is enabled.

### 2. Send Verification Email
```bash
POST /v1/email/send-verification
Authorization: Bearer <session_token>
```

### 3. Verify Email with OTP
```bash
POST /v1/email/verify
Authorization: Bearer <session_token>
{
  "otp_code": "123456"
}
```

### 4. Access API Key (after verification)
```bash
GET /v1/users/api-key
Authorization: Bearer <session_token>
```

## 🔐 Security Features

### Email Verification Enforcement
- **API Key Access**: Requires email verification when enabled
- **Chat Completions**: Requires verified email for API access
- **Rate Limiting**: 3 verification emails per day per user
- **OTP Expiry**: 24-hour default expiry for security

### Account Security
- **Password Policies**: Strong password requirements
- **Account Locking**: 5 failed attempts lock account for 1 hour
- **Session Management**: Secure session tokens with expiry
- **Security Logging**: All security events logged to MongoDB

## 🐳 Docker Deployment

### Docker Compose Configuration

The `docker-compose.yml` has been updated with MongoDB configuration:

```yaml
services:
  promptenchanter2:
    environment:
      - MONGODB_URL=mongodb+srv://your-connection-string
      - MONGODB_DATABASE=promptenchanter
      - USE_MONGODB=true
      - EMAIL_VERIFICATION_ENABLED=true
```

### Building and Running

```bash
# Build the container
docker-compose build

# Start the services
docker-compose up -d

# Check logs
docker-compose logs -f promptenchanter2
```

## 🧪 Testing

### Comprehensive Test Script

Run the MongoDB system test:

```bash
python test_mongodb_system.py
```

This test covers:
- MongoDB connection
- User registration and login
- Email verification flow
- API key validation
- Admin creation and management
- User management functions

### Manual Testing

1. **Register a user**:
   ```bash
   curl -X POST http://localhost:8000/v1/users/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "name": "Test User",
       "email": "test@example.com",
       "password": "TestPassword123!"
     }'
   ```

2. **Login and get session token**:
   ```bash
   curl -X POST http://localhost:8000/v1/users/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "TestPassword123!"
     }'
   ```

3. **Send verification email**:
   ```bash
   curl -X POST http://localhost:8000/v1/email/send-verification \
     -H "Authorization: Bearer <session_token>"
   ```

4. **Get API key (after verification)**:
   ```bash
   curl -X GET http://localhost:8000/v1/users/api-key \
     -H "Authorization: Bearer <session_token>"
   ```

## 🔄 Migration from SQLite

### Automatic Fallback
- If MongoDB connection fails, the system automatically falls back to SQLite
- Both systems can run simultaneously during migration
- Legacy endpoints remain available

### Data Migration
To migrate existing SQLite data to MongoDB, you can:

1. Export data from SQLite
2. Transform to MongoDB format
3. Import using MongoDB tools or custom scripts

### Gradual Migration
- Start with MongoDB enabled alongside SQLite
- Test thoroughly with new endpoints
- Gradually migrate users to new system
- Disable SQLite when ready

## 📊 Monitoring and Logging

### Security Events
All security events are logged to the `security_logs` collection:
- User registrations
- Login attempts (successful and failed)
- Email verifications
- API key regenerations
- Admin actions

### Health Checks
- MongoDB connection health check
- Email service status
- System component status

## 🚨 Troubleshooting

### MongoDB Connection Issues
1. Check MongoDB URL in environment variables
2. Verify network connectivity
3. Check MongoDB Atlas IP whitelist
4. Review connection logs

### Email Verification Issues
1. Verify SMTP configuration
2. Check email service logs
3. Confirm email delivery (check spam folder)
4. Verify rate limiting settings

### API Key Access Denied
1. Check if email verification is enabled
2. Verify user's email verification status
3. Confirm user has completed verification flow

## 🎯 Next Steps

1. **Production Deployment**: Configure production MongoDB cluster
2. **Email Service**: Set up production SMTP service (SendGrid, etc.)
3. **Monitoring**: Implement comprehensive monitoring and alerting
4. **Backup Strategy**: Set up automated MongoDB backups
5. **Performance Optimization**: Monitor and optimize database queries

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs -f promptenchanter2`
2. Run the test script: `python test_mongodb_system.py`
3. Review this documentation
4. Check MongoDB Atlas dashboard for connection issues

---

**Note**: This migration maintains backward compatibility while providing enhanced functionality. The system can operate with both SQLite and MongoDB simultaneously during the transition period.