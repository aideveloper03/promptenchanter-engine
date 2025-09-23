#!/usr/bin/env python3
"""
PromptEnchanter User Management Setup Script
"""
import os
import sys
import sqlite3
import secrets
import hashlib
from pathlib import Path
from datetime import datetime

def create_env_file():
    """Create .env file with secure defaults"""
    env_content = f"""# PromptEnchanter User Management Configuration

# Security Keys (CHANGE THESE IN PRODUCTION!)
SECRET_KEY={secrets.token_urlsafe(64)}
JWT_SECRET={secrets.token_urlsafe(64)}
MASTER_KEY={secrets.token_urlsafe(32)}

# Database Configuration
DATABASE_PATH=user_management.db

# API Configuration
API_KEY=sk-78912903
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=sk-Xf6CNfK8A4bCmoRAE8pBRCKyEJrJKigjlVlqCtf07AZmpije

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# Cache Settings
CACHE_TTL_SECONDS=3600
RESEARCH_CACHE_TTL_SECONDS=86400

# Concurrency Settings
MAX_CONCURRENT_REQUESTS=50
BATCH_MAX_PARALLEL_TASKS=10

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_VERIFICATION_ENABLED=false

# Firewall Settings
WHITELIST_MODE_ENABLED=false
AUTO_BLOCK_ENABLED=true
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ Created .env file with secure defaults")
    print("⚠️  IMPORTANT: Change the default keys in production!")

def setup_database():
    """Setup the user management database"""
    print("Setting up user management database...")
    
    # Import after ensuring the module path is correct
    sys.path.append(str(Path(__file__).parent))
    from app.database.models import db_manager
    
    # Database is automatically initialized when db_manager is imported
    print("✓ User management database initialized")
    
    # Create default admin if it doesn't exist
    try:
        from app.services.admin_service import admin_service
        print("✓ Default admin account created (username: admin, password: Admin123!)")
        print("⚠️  SECURITY WARNING: Change the default admin password immediately!")
    except Exception as e:
        print(f"⚠️  Warning: Could not create default admin: {e}")

def create_firewall_config():
    """Create firewall configuration file"""
    firewall_config = {
        "whitelist_enabled": False,
        "auto_block_enabled": True,
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000,
        "rules": []
    }
    
    import json
    with open('firewall_config.json', 'w') as f:
        json.dump(firewall_config, f, indent=2)
    
    print("✓ Created firewall configuration")

def create_startup_script():
    """Create startup script"""
    startup_script = """#!/bin/bash
# PromptEnchanter Startup Script

echo "Starting PromptEnchanter User Management System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the application
echo "Starting PromptEnchanter..."
python main.py
"""
    
    with open('start.sh', 'w') as f:
        f.write(startup_script)
    
    os.chmod('start.sh', 0o755)
    print("✓ Created startup script (start.sh)")

def create_docker_compose():
    """Create enhanced Docker Compose file"""
    docker_compose_content = """version: '3.8'

services:
  promptenchanter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_PATH=/app/data/user_management.db
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
      - ./firewall_config.json:/app/firewall_config.json
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - promptenchanter
    restart: unless-stopped

volumes:
  redis_data:
"""
    
    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose_content)
    
    print("✓ Updated Docker Compose configuration")

def create_documentation():
    """Create comprehensive documentation"""
    user_guide = """# PromptEnchanter User Management System

## Overview

PromptEnchanter now includes a comprehensive user management system with advanced security features, API key authentication, message logging, and admin/support staff capabilities.

## Features

### User Management
- **User Registration**: Secure registration with password validation
- **User Authentication**: JWT-based session management
- **API Key Management**: Unique API keys for each user with regeneration capability
- **Profile Management**: Users can update their profiles and settings
- **Account Deletion**: Secure account deletion with backup storage

### Security Features
- **Advanced Encryption**: AES encryption for sensitive data
- **IP Firewall**: Configurable IP whitelisting and blocking
- **Rate Limiting**: Multiple rate limiting strategies
- **Password Security**: Strong password requirements and hashing
- **Session Management**: Secure session handling with expiration

### Message Logging
- **High-Performance Logging**: Batch processing for high-speed logging
- **Message Analytics**: Comprehensive message statistics and analytics
- **User Activity Tracking**: Detailed user activity logs
- **Automatic Cleanup**: Configurable data retention policies

### Admin Control Panel
- **User Management**: Full CRUD operations for user accounts
- **System Statistics**: Real-time system monitoring
- **Security Monitoring**: Security event tracking and alerting
- **Firewall Management**: Dynamic IP management and rules

### Support Staff System
- **Role-Based Access**: Three levels of support staff permissions
- **User Support**: Tools for helping users with account issues
- **Limited Access**: Restricted access based on staff level
- **Audit Logging**: All support actions are logged

## Quick Start

### 1. Setup
```bash
# Run the setup script
python setup_user_management.py

# Start the application
./start.sh
```

### 2. Default Admin Account
- **Username**: admin
- **Password**: Admin123!
- **⚠️ Change this password immediately after first login!**

### 3. API Endpoints

#### User Management
- `POST /user/register` - Register new user
- `POST /user/login` - User login
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update user profile
- `GET /user/api-key` - Get encrypted API key
- `POST /user/regenerate-api-key` - Regenerate API key
- `POST /user/change-password` - Change password
- `DELETE /user/account` - Delete account

#### Chat API (with authentication)
- `POST /v1/chat/completions` - Create chat completion (requires API key)

#### Admin Panel
- `POST /admin/login` - Admin login
- `GET /admin/stats` - System statistics
- `GET /admin/users` - List all users
- `PUT /admin/users/{username}` - Update user
- `DELETE /admin/users/{username}` - Delete user
- `POST /admin/support-staff` - Create support staff

#### Support Staff
- `POST /support/login` - Support staff login
- `GET /support/users/search` - Search users
- `GET /support/users/{username}` - Get user info
- `PUT /support/users/{username}/email` - Update user email
- `PUT /support/users/{username}/password` - Reset user password

## Configuration

### Environment Variables
```bash
# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
MASTER_KEY=your-master-key

# Database
DATABASE_PATH=user_management.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Features
EMAIL_VERIFICATION_ENABLED=false
WHITELIST_MODE_ENABLED=false
AUTO_BLOCK_ENABLED=true
```

### User Registration Example
```bash
curl -X POST "http://localhost:8000/user/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "testuser",
    "name": "Test User",
    "email": "test@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "user_type": "Personal"
  }'
```

### API Usage Example
```bash
# Login to get session token
curl -X POST "http://localhost:8000/user/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Use API key for chat completions
curl -X POST "http://localhost:8000/v1/chat/completions" \\
  -H "Authorization: Bearer pe-your-api-key-here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "level": "medium",
    "messages": [
      {"role": "user", "content": "Hello, world!"}
    ],
    "r_type": "bpe"
  }'
```

## Database Schema

### Users Table
- username (PRIMARY KEY)
- name, email, password_hash
- about_me, hobbies, user_type
- subscription_plan, credits, limits
- access_rtype, level, additional_notes
- key (unique API key), time_created
- is_active, email_verified, last_login

### Message Logs Table
- log_id (PRIMARY KEY)
- username, email, model
- messages (JSON), research_model
- time, tokens_used, processing_time_ms

### Admin/Support Tables
- Separate tables for admin and support staff
- Role-based permissions and access control

## Security Best Practices

1. **Change Default Credentials**: Immediately change the default admin password
2. **Use HTTPS**: Always use HTTPS in production
3. **Secure Environment Variables**: Keep sensitive keys secure
4. **Regular Updates**: Keep dependencies updated
5. **Monitor Logs**: Regularly check security logs
6. **Backup Data**: Regular database backups
7. **IP Whitelisting**: Use IP whitelisting for admin access

## Support

For issues or questions:
1. Check the logs in `/logs/` directory
2. Review the security events in admin panel
3. Check the firewall configuration
4. Verify environment variables

## License

This enhanced version maintains the same license as the original PromptEnchanter project.
"""
    
    with open('USER_MANAGEMENT_GUIDE.md', 'w') as f:
        f.write(user_guide)
    
    print("✓ Created comprehensive user guide")

def main():
    """Main setup function"""
    print("🚀 Setting up PromptEnchanter User Management System...")
    print()
    
    try:
        # Create data directory
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Setup components
        create_env_file()
        setup_database()
        create_firewall_config()
        create_startup_script()
        create_docker_compose()
        create_documentation()
        
        print()
        print("✅ Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Review and update the .env file with your configuration")
        print("2. Change the default admin password (admin/Admin123!)")
        print("3. Configure your firewall rules if needed")
        print("4. Start the application with: ./start.sh")
        print("5. Access the API documentation at: http://localhost:8000/docs")
        print()
        print("📖 Read USER_MANAGEMENT_GUIDE.md for detailed instructions")
        print("🔒 Review security settings before production deployment")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()