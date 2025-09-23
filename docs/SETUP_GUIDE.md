# PromptEnchanter Setup Guide

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- Redis (optional but recommended)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd promptenchanter

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
```

### 3. Environment Configuration

Edit the `.env` file with your settings:

```env
# Basic Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite+aiosqlite:///./promptenchanter.db

# External API
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=your-wapi-key-here

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
FIREWALL_ENABLED=true
IP_WHITELIST_ENABLED=false

# User Management
USER_REGISTRATION_ENABLED=true
EMAIL_VERIFICATION_ENABLED=false

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Credit Management
AUTO_CREDIT_RESET_ENABLED=true
DAILY_USAGE_RESET_HOUR=0
```

### 4. Database & Admin Setup

```bash
# Create the first admin user
python scripts/create_admin.py
```

Follow the prompts to create your admin account:
- Enter admin username
- Enter admin full name  
- Enter admin email
- Create a secure password
- Confirm the password

### 5. Start Redis (Optional)

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:alpine

# Or using local installation
# Ubuntu/Debian: sudo systemctl start redis-server
# macOS: brew services start redis
```

### 6. Start the Server

```bash
# Development mode
python main.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Verify Installation

Visit `http://localhost:8000/docs` to see the API documentation.

Test the health endpoint:
```bash
curl http://localhost:8000/health
```

## User Registration

### Register Your First User

```bash
curl -X POST "http://localhost:8000/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "name": "Test User",
    "email": "test@example.com",
    "password": "SecurePass123",
    "user_type": "Personal"
  }'
```

### Test API Access

Use the API key from registration:

```bash
curl -X POST "http://localhost:8000/v1/prompt/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pe-your-api-key-here" \
  -d '{
    "level": "low",
    "messages": [{"role": "user", "content": "Hello!"}],
    "r_type": "bpe"
  }'
```

## Admin Panel Access

### Login as Admin

```bash
curl -X POST "http://localhost:8000/v1/admin-panel/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-admin-username",
    "password": "your-admin-password"
  }'
```

### Access Admin Features

With the admin session token, you can:

- View all users: `GET /v1/admin-panel/users`
- Get system statistics: `GET /v1/admin-panel/statistics`
- View security logs: `GET /v1/admin-panel/security-logs`
- Manage user accounts: `PUT /v1/admin-panel/users/{id}`

## Configuration Options

### Security Settings

```env
# Enable/disable user registration
USER_REGISTRATION_ENABLED=true

# Enable IP whitelisting (production recommended)
IP_WHITELIST_ENABLED=false

# Firewall protection
FIREWALL_ENABLED=true
MAX_FAILED_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_HOURS=1
```

### Session Management

```env
# Session duration for regular users
SESSION_DURATION_HOURS=24
REFRESH_TOKEN_DURATION_DAYS=30

# Admin sessions (shorter for security)
ADMIN_SESSION_DURATION_HOURS=24

# Support staff sessions
SUPPORT_SESSION_DURATION_HOURS=12
```

### Message Logging

```env
# Enable message logging
MESSAGE_LOGGING_ENABLED=true

# Batch processing settings
MESSAGE_BATCH_SIZE=50
MESSAGE_FLUSH_INTERVAL_SECONDS=600
MESSAGE_MAX_QUEUE_SIZE=1000
```

### Credit System

```env
# Enable automatic daily credit reset
AUTO_CREDIT_RESET_ENABLED=true

# Hour of day for reset (UTC)
DAILY_USAGE_RESET_HOUR=0

# Default credits for new users
DEFAULT_USER_CREDITS={"main": 5, "reset": 5}
DEFAULT_USER_LIMITS={"conversation_limit": 10, "reset": 10}
```

## Production Deployment

### Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  promptenchanter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/promptenchanter.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

Run with:
```bash
docker-compose up -d
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.promptenchanter.net;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/HTTPS Setup

```bash
# Using Certbot for Let's Encrypt
sudo certbot --nginx -d api.promptenchanter.net
```

### Environment Variables for Production

```env
# Security
DEBUG=false
SECRET_KEY=your-super-secure-production-key
IP_WHITELIST_ENABLED=true

# Database (use PostgreSQL for production)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/promptenchanter

# Logging
LOG_LEVEL=WARNING

# Email (for future features)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@promptenchanter.com
```

## Monitoring & Maintenance

### Log Files

Logs are written to:
- Console output (development)
- Structured JSON logs (production)

Monitor with:
```bash
tail -f /var/log/promptenchanter/app.log
```

### Database Backup

```bash
# SQLite backup
cp promptenchanter.db promptenchanter_backup_$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump promptenchanter > backup_$(date +%Y%m%d).sql
```

### Health Checks

Set up monitoring for:
- `/health` endpoint
- Database connectivity
- Redis connectivity
- API response times

### Credit Reset Monitoring

Monitor the automatic credit reset:
```bash
# Check service status
curl "http://localhost:8000/v1/admin-panel/statistics" \
  -H "Authorization: Bearer <admin-token>"
```

## Troubleshooting

### Common Issues

**"Database connection failed"**
- Check DATABASE_URL format
- Ensure database file permissions
- Verify SQLite installation

**"Redis connection failed"**
- Check Redis is running: `redis-cli ping`
- Verify REDIS_URL configuration
- Check network connectivity

**"WAPI authentication failed"**
- Verify WAPI_KEY is correct
- Check WAPI_URL endpoint
- Test external API connectivity

**"Permission denied" errors**
- Check file permissions on database
- Ensure write access to log directory
- Verify user permissions

### Debug Mode

Enable debug mode for troubleshooting:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Reset Admin Password

If you forget the admin password:

```bash
# Recreate admin user
python scripts/create_admin.py
```

## Support

For additional help:
1. Check the logs for error details
2. Review the [User Management Guide](USER_MANAGEMENT_GUIDE.md)
3. Verify configuration in `.env`
4. Test individual components (Redis, database, WAPI)
5. Check GitHub issues and documentation

## Next Steps

After setup:
1. Create user accounts for your team
2. Set up IP whitelisting for production
3. Configure email settings for notifications
4. Set up monitoring and alerting
5. Create regular database backups
6. Review security logs regularly