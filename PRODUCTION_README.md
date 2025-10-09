# PromptEnchanter - Production Deployment with Docker & SSL/HTTPS

This repository includes a complete production-ready setup for PromptEnchanter with Docker containerization and automated SSL certificate management using Let's Encrypt/Certbot.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- A registered domain name pointing to your server
- Ports 80 and 443 open in your firewall

### 1. Configure Environment

Edit `.env` file and set these required variables:

```bash
# Domain Configuration
DOMAIN=yourdomain.com
CERTBOT_EMAIL=admin@yourdomain.com

# Security (CHANGE THESE!)
SECRET_KEY=your-super-secret-key-here
API_KEY=your-api-key-here
REDIS_PASSWORD=your-redis-password

# Admin Account (CHANGE PASSWORD!)
DEFAULT_ADMIN_PASSWORD=YourStrongPasswordHere!
```

### 2. Initialize SSL Certificates

```bash
./init-letsencrypt.sh
```

This will:
- Set up Let's Encrypt SSL certificates
- Configure nginx for HTTPS
- Start the application with SSL enabled

### 3. Start Production Services

```bash
./start-production.sh
```

Your application is now accessible at:
- **HTTPS**: `https://yourdomain.com`
- **API Docs**: `https://yourdomain.com/docs`
- **Health Check**: `https://yourdomain.com/health`

## 📋 Available Scripts

### Production Management

| Script | Description |
|--------|-------------|
| `./start-production.sh` | Start all production services |
| `./start-production.sh --build` | Rebuild and start services |
| `./start-production.sh --logs` | Start and show logs |
| `./stop-production.sh` | Stop all services |
| `./stop-production.sh --remove-volumes` | Stop and remove all data |

### SSL Certificate Management

| Script | Description |
|--------|-------------|
| `./init-letsencrypt.sh` | Initialize SSL certificates (first time) |
| `./renew-certificates.sh` | Manually renew SSL certificates |
| `STAGING=1 ./init-letsencrypt.sh` | Test with staging certificates |

## 🏗️ Architecture

### Services

1. **promptenchanter2** - Main FastAPI application
   - Handles all API requests
   - Connects to MongoDB Atlas
   - Health checks enabled

2. **redis2** - Redis cache server
   - Session storage
   - API response caching
   - Password protected

3. **nginx2** - Reverse proxy
   - SSL/TLS termination
   - Rate limiting
   - Request routing
   - Security headers

4. **certbot** - SSL certificate management
   - Automatic certificate renewal (every 12 hours)
   - Let's Encrypt integration

### Docker Files

- `docker-compose.production.yml` - Production configuration
- `Dockerfile` - Application container image
- `nginx.prod.conf` - Production nginx configuration
- `.env` - Environment variables (keep secure!)

## 🔐 SSL/HTTPS Setup

### Automatic Certificate Renewal

Certificates are automatically renewed every 12 hours by the Certbot service. No manual intervention required.

### Manual Operations

```bash
# Check certificate status
docker-compose -f docker-compose.production.yml exec certbot certbot certificates

# Force renewal
./renew-certificates.sh

# View certbot logs
docker-compose -f docker-compose.production.yml logs certbot
```

## 📊 Monitoring & Logs

### View Logs

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f promptenchanter2
docker-compose -f docker-compose.production.yml logs -f nginx2
docker-compose -f docker-compose.production.yml logs -f redis2
```

### Health Checks

```bash
# Application health
curl https://yourdomain.com/health

# Service status
docker-compose -f docker-compose.production.yml ps

# Resource usage
docker stats
```

## 🔧 Common Operations

### Update Application

```bash
# Pull latest changes
git pull origin main

# Restart with rebuild
./stop-production.sh
./start-production.sh --build
```

### Backup Data

```bash
# Backup volumes
docker run --rm -v promptenchanter_redis_data2:/data -v $(pwd)/backups:/backup alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz /data

# Export MongoDB (if using local MongoDB)
# MongoDB Atlas has automatic backups
```

### Scale Services

```bash
# Scale application instances
docker-compose -f docker-compose.production.yml up -d --scale promptenchanter2=3
```

## 🐛 Troubleshooting

### SSL Certificate Issues

```bash
# Check certificate files
ls -la ./certbot/conf/live/yourdomain.com/

# Verify DNS
nslookup yourdomain.com

# Re-initialize certificates
./init-letsencrypt.sh
```

### Nginx Issues

```bash
# Test configuration
docker-compose -f docker-compose.production.yml exec nginx2 nginx -t

# Reload configuration
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload

# Check logs
docker-compose -f docker-compose.production.yml logs nginx2
```

### Application Issues

```bash
# Check application logs
docker-compose -f docker-compose.production.yml logs promptenchanter2

# Restart application
docker-compose -f docker-compose.production.yml restart promptenchanter2

# Check health
curl https://yourdomain.com/health
```

### Redis Connection Issues

```bash
# Test Redis
docker-compose -f docker-compose.production.yml exec redis2 redis-cli ping

# Check Redis logs
docker-compose -f docker-compose.production.yml logs redis2
```

## 🔒 Security Features

### Implemented Security

- ✅ SSL/TLS encryption (HTTPS)
- ✅ Automatic certificate renewal
- ✅ Rate limiting at nginx level
- ✅ Security headers (HSTS, X-Frame-Options, etc.)
- ✅ Password-protected Redis
- ✅ Non-root container execution
- ✅ Docker resource limits
- ✅ Log rotation

### Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure firewall (UFW/iptables)
- [ ] Enable email verification
- [ ] Set up monitoring/alerting
- [ ] Regular security updates
- [ ] Review rate limits
- [ ] Implement backup strategy

## 📈 Performance Tuning

### Nginx Optimization

Already configured in `nginx.prod.conf`:
- HTTP/2 enabled
- Gzip compression
- Connection keep-alive
- Request buffering

### Application Scaling

```bash
# Increase workers (edit docker-compose.production.yml)
environment:
  - WORKERS=4  # Add this

# Scale horizontally
docker-compose -f docker-compose.production.yml up -d --scale promptenchanter2=3
```

### Redis Tuning

```bash
# Increase memory (edit docker-compose.production.yml)
deploy:
  resources:
    limits:
      memory: 1G  # Increase from 512M
```

## 📚 Documentation

- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Detailed deployment guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API reference
- **Application Docs**: `https://yourdomain.com/docs`

## 🆘 Support

### Quick Commands Reference

```bash
# Start production
./start-production.sh

# Stop production
./stop-production.sh

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Renew SSL
./renew-certificates.sh

# Check status
docker-compose -f docker-compose.production.yml ps

# Clean up
docker system prune -a
```

### Getting Help

1. Check logs: `docker-compose -f docker-compose.production.yml logs`
2. Review [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
3. Test SSL: `https://www.ssllabs.com/ssltest/`
4. Check firewall: `sudo ufw status`

## 📝 Environment Variables

### Required Variables

```bash
# Domain & SSL
DOMAIN=yourdomain.com
CERTBOT_EMAIL=admin@yourdomain.com

# Security
SECRET_KEY=your-secret-key
API_KEY=your-api-key
REDIS_PASSWORD=redis-password

# MongoDB (already configured)
MONGODB_URL=mongodb+srv://...
MONGODB_DATABASE=promptenchanter
USE_MONGODB=true
```

### Optional Variables

```bash
# Email (if EMAIL_VERIFICATION_ENABLED=true)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

## 🎯 Production Checklist

Before going live:

- [ ] Domain DNS configured and propagated
- [ ] Firewall configured (ports 80, 443 open)
- [ ] `.env` file properly configured
- [ ] All default passwords changed
- [ ] SSL certificates initialized
- [ ] Health checks passing
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Documentation reviewed

---

**🎉 Your PromptEnchanter application is production-ready!**

For detailed instructions, see [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
