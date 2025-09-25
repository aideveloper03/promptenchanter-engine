# PromptEnchanter Docker Deployment Guide

This guide provides comprehensive instructions for deploying PromptEnchanter using Docker and Docker Compose.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Production Deployment](#production-deployment)
5. [Development Setup](#development-setup)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)
8. [Monitoring and Logging](#monitoring-and-logging)

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Disk Space**: Minimum 5GB free space
- **CPU**: 2+ cores recommended
- **Network**: Internet access for AI API calls

### Required Services

- **WAPI Access**: Valid API key for external AI service
- **Domain** (Production): Domain name for SSL/TLS configuration

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd promptenchanter

# Create necessary directories
mkdir -p logs data ssl

# Copy environment configuration
cp .env.example .env
```

### 2. Configure Environment

Edit the `.env` file with your configuration:

```bash
# Required: Configure your WAPI credentials
WAPI_URL=https://your-ai-api-endpoint.com/v1/chat/completions
WAPI_KEY=your-api-key-here

# Required: Change the secret key for production
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars

# Optional: Configure other settings as needed
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","service":"PromptEnchanter","version":"1.0.0"}
```

## Configuration

### Environment Variables

#### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `WAPI_URL` | External AI API endpoint | `https://api.openai.com/v1/chat/completions` |
| `WAPI_KEY` | API key for external service | `sk-...` |
| `SECRET_KEY` | JWT secret key (32+ chars) | `your-secure-secret-key` |

#### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `DATABASE_URL` | SQLite path | Database connection URL |

### Database Configuration

#### SQLite (Default - Development)
```env
DATABASE_URL=sqlite+aiosqlite:///./data/promptenchanter.db
```

#### PostgreSQL (Recommended - Production)
```env
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/promptenchanter
```

### Redis Configuration

```env
# Default (Docker internal)
REDIS_URL=redis://redis:6379/0

# External Redis
REDIS_URL=redis://your-redis-host:6379/0

# Redis with auth
REDIS_URL=redis://:password@redis-host:6379/0
```

## Production Deployment

### 1. Security Configuration

```env
# Production security settings
DEBUG=false
SECRET_KEY=your-very-long-and-secure-secret-key-minimum-32-characters
FIREWALL_ENABLED=true
IP_WHITELIST_ENABLED=false
```

### 2. Database Setup (PostgreSQL)

Add PostgreSQL to your `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: promptenchanter
      POSTGRES_USER: promptenchanter
      POSTGRES_PASSWORD: your-secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - promptenchanter-network
    healthcheck:
      test: ["CMD-READY", "pg_isready", "-U", "promptenchanter"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Update environment:
```env
DATABASE_URL=postgresql+asyncpg://promptenchanter:your-secure-password@postgres:5432/promptenchanter
```

### 3. SSL/TLS Configuration

#### Option A: Let's Encrypt with Nginx

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - promptenchanter
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    command: certonly --webroot --webroot-path=/var/www/certbot --email your-email@domain.com --agree-tos --no-eff-email -d your-domain.com

volumes:
  certbot_certs:
  certbot_www:
```

#### Option B: Custom SSL Certificates

Place your SSL certificates in the `ssl/` directory:
```
ssl/
├── fullchain.pem
└── privkey.pem
```

### 4. Production nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream promptenchanter {
        server promptenchanter:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://promptenchanter;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_timeout 120s;
        }

        location /health {
            proxy_pass http://promptenchanter/health;
            access_log off;
        }
    }
}
```

### 5. Deploy Production

```bash
# Deploy with production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose logs -f promptenchanter nginx
```

## Development Setup

### 1. Development Configuration

```env
DEBUG=true
LOG_LEVEL=DEBUG
AUTO_RELOAD=true
```

### 2. Development Docker Compose

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  promptenchanter:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /app/__pycache__
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Development Dockerfile

Create `Dockerfile.dev`:

```dockerfile
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 4. Start Development

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied Errors

```bash
# Fix directory permissions
sudo chown -R $USER:$USER logs data ssl
chmod 755 logs data ssl
```

#### 2. Database Connection Issues

```bash
# Check database container
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U promptenchanter -d promptenchanter
```

#### 3. Redis Connection Issues

```bash
# Check Redis container
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### 4. WAPI Connection Issues

```bash
# Check network connectivity
docker-compose exec promptenchanter curl -I https://your-wapi-url.com

# Check API key configuration
docker-compose exec promptenchanter env | grep WAPI
```

#### 5. Health Check Failures

```bash
# Check application logs
docker-compose logs promptenchanter

# Test health endpoint manually
curl -v http://localhost:8000/health
```

### Debugging Commands

```bash
# View all container logs
docker-compose logs

# Follow logs for specific service
docker-compose logs -f promptenchanter

# Execute commands in container
docker-compose exec promptenchanter bash

# Check container resource usage
docker stats

# Inspect container configuration
docker-compose config

# Restart specific service
docker-compose restart promptenchanter
```

## Security Considerations

### 1. Environment Security

- **Never commit `.env` files** to version control
- **Use strong SECRET_KEY** (32+ characters)
- **Rotate API keys** regularly
- **Enable firewall** in production
- **Use HTTPS** for all production traffic

### 2. Network Security

```yaml
# Disable external Redis port in production
# Comment out or remove:
# ports:
#   - "6379:6379"
```

### 3. Container Security

```bash
# Run as non-root user (already configured)
USER appuser

# Limit container resources
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### 4. SSL/TLS Configuration

- **Use TLS 1.2+** only
- **Implement HSTS** headers
- **Use strong cipher suites**
- **Implement certificate pinning** if applicable

## Monitoring and Logging

### 1. Log Management

```yaml
# Configure log rotation
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 2. Health Monitoring

```bash
# Check all service health
docker-compose ps

# Monitor health endpoints
watch -n 5 'curl -s http://localhost:8000/health | jq'
```

### 3. Metrics Collection

Add monitoring stack to `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

### 4. Backup Strategy

```bash
# Backup database (SQLite)
docker-compose exec promptenchanter cp /app/data/promptenchanter.db /app/data/backup-$(date +%Y%m%d).db

# Backup database (PostgreSQL)
docker-compose exec postgres pg_dump -U promptenchanter promptenchanter > backup-$(date +%Y%m%d).sql

# Backup Redis data
docker-compose exec redis redis-cli BGSAVE
```

## Scaling and High Availability

### 1. Horizontal Scaling

```yaml
# Scale application instances
services:
  promptenchanter:
    deploy:
      replicas: 3
    environment:
      - WORKERS=1  # Single worker per container
```

### 2. Load Balancing

```nginx
upstream promptenchanter {
    server promptenchanter_1:8000;
    server promptenchanter_2:8000;
    server promptenchanter_3:8000;
}
```

### 3. High Availability Setup

```yaml
# Redis cluster setup
redis-cluster:
  image: redis:7-alpine
  command: redis-server --port 7000 --cluster-enabled yes
  deploy:
    replicas: 6
```

## Maintenance

### 1. Updates and Upgrades

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Clean unused images
docker image prune -f
```

### 2. Database Maintenance

```bash
# Run database migrations
docker-compose exec promptenchanter python -m alembic upgrade head

# Backup before maintenance
docker-compose exec postgres pg_dump -U promptenchanter promptenchanter > pre-maintenance-backup.sql
```

### 3. Log Rotation

```bash
# Manual log cleanup
docker-compose logs --tail=0 -f > /dev/null &
docker system prune -f
```

## Support and Documentation

- **API Documentation**: `/docs` (Swagger UI)
- **Health Check**: `/health`
- **Metrics**: `/metrics` (if enabled)
- **Repository**: `<repository-url>`
- **Issues**: `<repository-url>/issues`

For additional support, please refer to the project documentation or create an issue in the repository.