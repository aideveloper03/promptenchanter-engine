# PromptEnchanter Deployment Guide

This guide covers various deployment options for PromptEnchanter in production environments.

## Prerequisites

- Docker and Docker Compose
- Redis instance (recommended)
- SSL certificates (for HTTPS)
- Domain name (optional)

## Environment Setup

### 1. Environment Variables

Create a production `.env` file:

```env
# PromptEnchanter Configuration
API_KEY=your-production-api-key-here
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=your-wapi-key-here

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-very-secure-secret-key-change-this
ALGORITHM=HS256

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# Cache Settings
CACHE_TTL_SECONDS=3600
RESEARCH_CACHE_TTL_SECONDS=86400

# Concurrency Settings
MAX_CONCURRENT_REQUESTS=50
BATCH_MAX_PARALLEL_TASKS=10
```

### 2. Security Considerations

- **API Key**: Generate a strong, unique API key
- **Secret Key**: Use a cryptographically secure secret key
- **WAPI Key**: Secure your external API credentials
- **SSL/TLS**: Always use HTTPS in production
- **Firewall**: Restrict access to necessary ports only

## Deployment Options

## Option 1: Docker Compose (Recommended)

### Basic Setup

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd promptenchanter
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   curl http://localhost/health
   ```

### Production Docker Compose

```yaml
version: '3.8'

services:
  promptenchanter:
    build: .
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    networks:
      - promptenchanter-network
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
      - ./redis.conf:/etc/redis/redis.conf
    networks:
      - promptenchanter-network
    command: redis-server /etc/redis/redis.conf
    deploy:
      resources:
        limits:
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - promptenchanter
    restart: unless-stopped
    networks:
      - promptenchanter-network

volumes:
  redis_data:

networks:
  promptenchanter-network:
    driver: bridge
```

## Option 2: Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: promptenchanter

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promptenchanter-config
  namespace: promptenchanter
data:
  REDIS_URL: "redis://redis:6379/0"
  HOST: "0.0.0.0"
  PORT: "8000"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  CACHE_TTL_SECONDS: "3600"
  RESEARCH_CACHE_TTL_SECONDS: "86400"
  MAX_CONCURRENT_REQUESTS: "50"
  BATCH_MAX_PARALLEL_TASKS: "10"
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: promptenchanter-secrets
  namespace: promptenchanter
type: Opaque
stringData:
  API_KEY: "your-production-api-key"
  WAPI_KEY: "your-wapi-key"
  SECRET_KEY: "your-secret-key"
```

### Redis Deployment

```yaml
# redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: promptenchanter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          limits:
            memory: "512Mi"
            cpu: "250m"
          requests:
            memory: "256Mi"
            cpu: "125m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: promptenchanter
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: promptenchanter
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### PromptEnchanter Deployment

```yaml
# promptenchanter.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: promptenchanter
  namespace: promptenchanter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: promptenchanter
  template:
    metadata:
      labels:
        app: promptenchanter
    spec:
      containers:
      - name: promptenchanter
        image: promptenchanter:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: promptenchanter-config
        - secretRef:
            name: promptenchanter-secrets
        resources:
          limits:
            memory: "1Gi"
            cpu: "500m"
          requests:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: promptenchanter-service
  namespace: promptenchanter
spec:
  selector:
    app: promptenchanter
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: promptenchanter-ingress
  namespace: promptenchanter
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.promptenchanter.net
    secretName: promptenchanter-tls
  rules:
  - host: api.promptenchanter.net
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: promptenchanter-service
            port:
              number: 80
```

## Option 3: AWS ECS Deployment

### Task Definition

```json
{
  "family": "promptenchanter",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "promptenchanter",
      "image": "your-ecr-repo/promptenchanter:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REDIS_URL",
          "value": "redis://your-elasticache-endpoint:6379/0"
        }
      ],
      "secrets": [
        {
          "name": "API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:promptenchanter/api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/promptenchanter",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Service Configuration

```json
{
  "serviceName": "promptenchanter-service",
  "cluster": "promptenchanter-cluster",
  "taskDefinition": "promptenchanter",
  "desiredCount": 3,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-12345", "subnet-67890"],
      "securityGroups": ["sg-abcdef"],
      "assignPublicIp": "ENABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:region:account:targetgroup/promptenchanter-tg",
      "containerName": "promptenchanter",
      "containerPort": 8000
    }
  ]
}
```

## Option 4: Google Cloud Run

### Dockerfile for Cloud Run

```dockerfile
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Deploy to Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/promptenchanter

# Deploy to Cloud Run
gcloud run deploy promptenchanter \
  --image gcr.io/PROJECT-ID/promptenchanter \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars REDIS_URL=redis://your-memorystore-ip:6379/0 \
  --max-instances 10 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300
```

## Monitoring and Logging

### Prometheus Metrics

Add to your application:

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

REQUEST_COUNT = Counter('promptenchanter_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('promptenchanter_request_duration_seconds', 'Request duration')
ACTIVE_REQUESTS = Gauge('promptenchanter_active_requests', 'Active requests')
RESEARCH_REQUESTS = Counter('promptenchanter_research_requests_total', 'Research requests')
CACHE_HITS = Counter('promptenchanter_cache_hits_total', 'Cache hits', ['cache_type'])
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "PromptEnchanter Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(promptenchanter_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(promptenchanter_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(promptenchanter_cache_hits_total[5m]) / rate(promptenchanter_requests_total[5m])",
            "legendFormat": "Cache Hit Rate"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

#### ELK Stack Configuration

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:7.14.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:7.14.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## Performance Optimization

### Redis Configuration

```conf
# redis.conf
# Memory optimization
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Network
tcp-keepalive 300
timeout 0

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
```

### Nginx Optimization

```nginx
# nginx.conf
worker_processes auto;
worker_connections 2048;

http {
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain application/json application/javascript text/css;

    # Connection pooling
    upstream promptenchanter {
        least_conn;
        server promptenchanter:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Caching
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m inactive=60m;

    server {
        listen 80;
        
        # API caching for GET requests
        location /v1/admin/health {
            proxy_cache api_cache;
            proxy_cache_valid 200 1m;
            proxy_pass http://promptenchanter;
        }

        # Rate limiting with different zones
        location /v1/prompt/ {
            limit_req zone=api burst=20 nodelay;
            limit_req_status 429;
            proxy_pass http://promptenchanter;
        }

        location /v1/batch/ {
            limit_req zone=batch burst=5 nodelay;
            limit_req_status 429;
            proxy_pass http://promptenchanter;
        }
    }
}
```

## Security Hardening

### 1. Network Security

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  promptenchanter:
    networks:
      - internal
    # Remove external port exposure

  nginx:
    ports:
      - "443:443"  # Only HTTPS
    networks:
      - internal
      - external

  redis:
    networks:
      - internal  # Internal only

networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge
```

### 2. SSL/TLS Configuration

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

### 3. Container Security

```dockerfile
# Security-hardened Dockerfile
FROM python:3.9-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install security updates
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Set secure file permissions
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Switch to non-root user
USER appuser

# Remove unnecessary packages
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Backup and Disaster Recovery

### Redis Backup

```bash
#!/bin/bash
# backup-redis.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/redis"
REDIS_HOST="localhost"
REDIS_PORT="6379"

mkdir -p $BACKUP_DIR

# Create backup
redis-cli -h $REDIS_HOST -p $REDIS_PORT --rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# Compress backup
gzip $BACKUP_DIR/redis_backup_$DATE.rdb

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.rdb.gz" -mtime +7 -delete

echo "Redis backup completed: redis_backup_$DATE.rdb.gz"
```

### Application Backup

```bash
#!/bin/bash
# backup-app.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/app"
APP_DIR="/app"

mkdir -p $BACKUP_DIR

# Backup configuration and logs
tar -czf $BACKUP_DIR/app_config_$DATE.tar.gz \
    $APP_DIR/.env \
    $APP_DIR/logs/ \
    $APP_DIR/docker-compose.yml

# Backup to S3 (optional)
aws s3 cp $BACKUP_DIR/app_config_$DATE.tar.gz \
    s3://your-backup-bucket/promptenchanter/

echo "Application backup completed: app_config_$DATE.tar.gz"
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats
   
   # Adjust Redis memory limit
   redis-cli CONFIG SET maxmemory 256mb
   ```

2. **Rate Limiting Issues**
   ```bash
   # Check rate limit logs
   docker logs nginx | grep "limiting requests"
   
   # Adjust rate limits in nginx.conf
   ```

3. **WAPI Connection Issues**
   ```bash
   # Test WAPI connectivity
   curl -H "Authorization: Bearer $WAPI_KEY" $WAPI_URL
   
   # Check application logs
   docker logs promptenchanter
   ```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

API_URL="https://api.promptenchanter.net"
API_KEY="your-api-key"

# Check main health endpoint
echo "Checking main health..."
curl -f $API_URL/health || exit 1

# Check authenticated health
echo "Checking authenticated health..."
curl -f -H "Authorization: Bearer $API_KEY" $API_URL/v1/admin/health || exit 1

# Check Redis connectivity
echo "Checking Redis..."
redis-cli ping || exit 1

echo "All health checks passed!"
```

This deployment guide provides comprehensive instructions for deploying PromptEnchanter in various production environments with proper security, monitoring, and maintenance procedures.