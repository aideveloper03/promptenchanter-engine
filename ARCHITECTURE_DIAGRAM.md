# PromptEnchanter Production Architecture

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                  │
│                    (Public Access via DNS)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   Port 80 (HTTP) │
                    │  Port 443 (HTTPS)│
                    └────────┬─────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                        NGINX REVERSE PROXY                           │
│  Container: nginx2 (nginx:alpine)                                    │
│                                                                       │
│  ✅ SSL/TLS Termination (Let's Encrypt)                              │
│  ✅ HTTP → HTTPS Redirect                                            │
│  ✅ Rate Limiting (100 req/min API, 25 req/min batch)                │
│  ✅ Security Headers (HSTS, CSP, X-Frame-Options)                    │
│  ✅ Gzip Compression                                                  │
│  ✅ HTTP/2 Support                                                    │
│  ✅ Request Buffering & Timeouts                                      │
│                                                                       │
│  Config: nginx.prod.conf                                             │
│  Volumes: ./certbot/conf (SSL certs), ./nginx/cache                  │
│  Resources: 0.5 CPU / 256MB RAM                                      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                    Internal Network
                    (promptenchanter2-network)
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                  PROMPTENCHANTER APPLICATION                         │
│  Container: promptenchanter2                                         │
│                                                                       │
│  🚀 FastAPI Backend (Python 3.9)                                     │
│  📡 API Endpoints (v1/prompt, v1/chat, v1/admin, v1/users)           │
│  🔐 Authentication & Authorization                                   │
│  💾 Session Management                                               │
│  📊 API Usage Tracking                                               │
│  ✉️  Email Service (optional)                                        │
│                                                                       │
│  Port: 8000 (internal)                                               │
│  Resources: 2 CPU / 2GB RAM                                          │
│  Volumes: ./logs (application logs), ./data (SQLite if used)         │
│  Health Check: /health endpoint                                      │
└───────────────┬────────────────────────────────┬─────────────────────┘
                │                                │
                │                                │
       ┌────────▼──────────┐          ┌─────────▼──────────────────┐
       │      REDIS        │          │    MONGODB ATLAS           │
       │   (redis2)        │          │   (External Cloud)         │
       │                   │          │                            │
       │ 📦 Caching        │          │ 📚 User Database           │
       │ 🔑 Sessions       │          │ 💬 Chat History            │
       │ 🚦 Rate Limiting  │          │ 📝 Message Logs            │
       │ 🔒 Password Auth  │          │ 👤 Admin/Support Users     │
       │                   │          │                            │
       │ Port: 6379        │          │ Connection: SRV protocol   │
       │ Persistence: AOF  │          │ Backup: Automated by Atlas │
       │ Resources:        │          │                            │
       │   1 CPU / 512MB   │          └────────────────────────────┘
       └───────────────────┘
                │
                │
       ┌────────▼──────────────────────────────────────────────────────┐
       │                    CERTBOT (SSL Manager)                       │
       │  Container: certbot                                            │
       │                                                                │
       │  🔐 Let's Encrypt Integration                                  │
       │  🔄 Auto-renewal (every 12 hours)                              │
       │  📜 Certificate Management                                      │
       │  ✅ Domain Validation (webroot)                                │
       │                                                                │
       │  Volumes: ./certbot/conf, ./certbot/www, ./certbot/logs        │
       │  Schedule: Runs renewal check every 12h                        │
       └────────────────────────────────────────────────────────────────┘
```

## 🔄 Request Flow

### HTTPS Request Flow

```
1. Client Request
   │
   ├─→ DNS Resolution: yourdomain.com → Server IP
   │
2. TLS Handshake
   │
   ├─→ Nginx: SSL Termination (Port 443)
   │   ├─→ Certificate: Let's Encrypt
   │   ├─→ Protocol: TLS 1.2/1.3
   │   └─→ Ciphers: Modern (ECDHE, AES-GCM)
   │
3. Request Processing
   │
   ├─→ Nginx: Security & Rate Limiting
   │   ├─→ Rate Limit Check
   │   ├─→ Security Headers Applied
   │   └─→ Request Buffering
   │
4. Proxy to Application
   │
   ├─→ FastAPI App (Port 8000)
   │   ├─→ Authentication Check
   │   ├─→ Session Validation (Redis)
   │   ├─→ Business Logic
   │   └─→ Database Query (MongoDB)
   │
5. Response
   │
   ├─→ Nginx: Compression & Caching
   │   ├─→ Gzip Compression
   │   └─→ Cache Headers
   │
6. Client Response
   │
   └─→ Encrypted Response (HTTPS)
```

### HTTP Request Flow (Redirect)

```
HTTP Request (Port 80)
   │
   ├─→ Nginx: HTTP Server
   │
   └─→ 301 Redirect → https://yourdomain.com
       (Exception: /.well-known/acme-challenge/ for Let's Encrypt)
```

## 📦 Data Flow & Persistence

```
┌─────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYERS                     │
└─────────────────────────────────────────────────────────────┘

1. Application Data (MongoDB Atlas - External)
   ├── Users & Authentication
   ├── Chat History & Conversations
   ├── Message Logs
   ├── Admin & Support Staff
   └── API Usage Statistics

2. Cache & Sessions (Redis - Container Volume)
   ├── Session Tokens
   ├── API Response Cache
   ├── Rate Limit Counters
   └── Temporary Data

3. Application Logs (Host Volume Mount)
   ├── ./logs/promptenchanter.log (application logs)
   └── Rotated automatically (max 5 files, 100MB each)

4. SSL Certificates (Host Volume Mount)
   ├── ./certbot/conf/live/yourdomain.com/
   │   ├── fullchain.pem
   │   ├── privkey.pem
   │   └── chain.pem
   └── Auto-renewed every 12 hours

5. SQLite Fallback (Host Volume Mount - Optional)
   └── ./data/promptenchanter2.db (used if MongoDB fails)
```

## 🔐 Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      SECURITY ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────┘

1. Network Layer
   ├── Firewall (UFW/iptables)
   │   ├── Port 80: HTTP (redirect only)
   │   ├── Port 443: HTTPS (encrypted)
   │   └── All other ports: CLOSED
   │
   └── Docker Network Isolation
       └── promptenchanter2-network (bridge)

2. Transport Layer (TLS/SSL)
   ├── TLS 1.2 and 1.3 only
   ├── Modern cipher suites
   ├── Perfect Forward Secrecy
   ├── OCSP Stapling
   └── Let's Encrypt certificates

3. Application Layer
   ├── JWT Token Authentication
   ├── Password Hashing (Argon2)
   ├── Session Management
   ├── API Key Validation
   └── Role-based Access Control

4. Nginx Security
   ├── Rate Limiting (per IP)
   ├── Connection Limits
   ├── Request Size Limits
   ├── Security Headers:
   │   ├── HSTS (Strict-Transport-Security)
   │   ├── Content-Security-Policy
   │   ├── X-Frame-Options: DENY
   │   ├── X-Content-Type-Options: nosniff
   │   └── X-XSS-Protection

5. Container Security
   ├── Non-root user execution
   ├── Resource limits (CPU/Memory)
   ├── Read-only configs
   └── Isolated networks
```

## 📊 Monitoring & Health Checks

```
┌─────────────────────────────────────────────────────────────┐
│                    HEALTH CHECK SYSTEM                      │
└─────────────────────────────────────────────────────────────┘

Application (promptenchanter2)
├── Endpoint: http://localhost:8000/health
├── Interval: 30 seconds
├── Timeout: 10 seconds
├── Retries: 3
└── Start Period: 40 seconds

Redis (redis2)
├── Command: redis-cli ping
├── Interval: 10 seconds
├── Timeout: 5 seconds
└── Retries: 5

Nginx (nginx2)
├── Endpoint: http://localhost/health
├── Interval: 30 seconds
├── Timeout: 10 seconds
└── Retries: 3

Dependency Chain:
nginx2 → promptenchanter2 → redis2
       (waits for healthy)
```

## 🔄 Auto-Renewal System

```
┌─────────────────────────────────────────────────────────────┐
│              SSL CERTIFICATE AUTO-RENEWAL                   │
└─────────────────────────────────────────────────────────────┘

Certbot Container (Background Process)
│
├─→ Every 12 hours:
│   ├── Check certificate expiry
│   ├── If < 30 days: Renew certificate
│   │   ├── Webroot validation: /.well-known/acme-challenge/
│   │   ├── Let's Encrypt verification
│   │   └── New certificates saved to ./certbot/conf/
│   └── Continue loop
│
└─→ Nginx Container (Background Process)
    ├── Every 6 hours:
    │   └── Reload nginx (nginx -s reload)
    │       └── Picks up renewed certificates
    └── Continue loop

Manual Renewal (if needed):
└─→ ./renew-certificates.sh
```

## 🚀 Deployment States

```
┌─────────────────────────────────────────────────────────────┐
│                  DEPLOYMENT LIFECYCLE                       │
└─────────────────────────────────────────────────────────────┘

1. INITIALIZATION
   ├── ./init-letsencrypt.sh
   │   ├── Create dummy certificate
   │   ├── Start nginx
   │   ├── Request real certificate
   │   └── Reload with real certificate

2. RUNNING (Normal Operation)
   ├── All containers: Running & Healthy
   ├── Nginx: Serving HTTPS traffic
   ├── App: Processing requests
   ├── Redis: Caching & sessions
   ├── Certbot: Background renewal checks
   └── Logs: Rotating automatically

3. MAINTENANCE
   ├── Updates: ./stop-production.sh && ./start-production.sh --build
   ├── Logs: docker-compose -f docker-compose.production.yml logs -f
   ├── Manual SSL Renewal: ./renew-certificates.sh
   └── Scaling: docker-compose up -d --scale promptenchanter2=N

4. SHUTDOWN
   └── ./stop-production.sh
       ├── Graceful container shutdown
       ├── Data persisted to volumes
       └── Ready for restart
```

## 📈 Resource Allocation

```
┌─────────────────────────────────────────────────────────────┐
│                    RESOURCE LIMITS                          │
└─────────────────────────────────────────────────────────────┘

Service           CPU (Limit)   Memory (Limit)   Restart Policy
─────────────────────────────────────────────────────────────
promptenchanter2     2.0           2GB           always
redis2               1.0           512MB         always
nginx2               0.5           256MB         always
certbot              -             -             unless-stopped

Total Maximum:       3.5 CPU       2.75GB RAM

Reservations (Minimum Guaranteed):
promptenchanter2     0.5 CPU       512MB
redis2               0.25 CPU      128MB
nginx2               0.1 CPU       64MB

Recommended Server: 4 CPU / 4GB RAM minimum
```

---

## 🎯 Key Architectural Decisions

1. **Nginx as Reverse Proxy**: Handles SSL termination, rate limiting, and security headers
2. **Let's Encrypt SSL**: Free, automated, and widely trusted certificates
3. **Redis for Caching**: Fast in-memory cache for sessions and API responses
4. **MongoDB Atlas**: Managed database for reliability and automatic backups
5. **Docker Compose**: Simple orchestration suitable for single-server deployments
6. **Health Checks**: Ensures service reliability and automatic recovery
7. **Resource Limits**: Prevents resource exhaustion and ensures stability
8. **Log Rotation**: Prevents disk space issues from log accumulation

---

This architecture provides a production-ready, secure, and scalable deployment
for the PromptEnchanter application with automated SSL/HTTPS management.
