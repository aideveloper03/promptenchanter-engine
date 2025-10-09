# Production Commands Reference

## 🚀 Deployment Commands

### Initial Setup
```bash
# 1. Configure environment
vim .env  # Set DOMAIN, CERTBOT_EMAIL, passwords

# 2. Make scripts executable (if needed)
chmod +x *.sh

# 3. Initialize SSL certificates
./init-letsencrypt.sh

# 4. Start production services
./start-production.sh
```

### Alternative: Manual Setup
```bash
# Build and start all services
docker-compose -f docker-compose.production.yml up -d --build

# View startup logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## 🔄 Service Management

### Start Services
```bash
# Quick start
./start-production.sh

# Start with rebuild
./start-production.sh --build

# Start and show logs
./start-production.sh --logs

# Manual start
docker-compose -f docker-compose.production.yml up -d
```

### Stop Services
```bash
# Graceful stop (keeps data)
./stop-production.sh

# Stop and remove volumes (DELETES DATA!)
./stop-production.sh --remove-volumes

# Manual stop
docker-compose -f docker-compose.production.yml down
```

### Restart Services
```bash
# Restart all services
docker-compose -f docker-compose.production.yml restart

# Restart specific service
docker-compose -f docker-compose.production.yml restart promptenchanter2
docker-compose -f docker-compose.production.yml restart nginx2
docker-compose -f docker-compose.production.yml restart redis2
```

---

## 🔐 SSL Certificate Management

### Initialize Certificates
```bash
# Production certificates
./init-letsencrypt.sh

# Staging/testing certificates (won't show as valid)
STAGING=1 ./init-letsencrypt.sh
```

### Renew Certificates
```bash
# Manual renewal (also reloads nginx)
./renew-certificates.sh

# Force renewal via docker
docker-compose -f docker-compose.production.yml exec certbot certbot renew --force-renewal
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload
```

### Check Certificate Status
```bash
# List certificates
docker-compose -f docker-compose.production.yml exec certbot certbot certificates

# Check expiration
docker-compose -f docker-compose.production.yml exec certbot certbot certificates | grep "Expiry Date"

# Verify SSL (external tool)
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

---

## 📊 Monitoring & Logs

### View Logs
```bash
# All services (follow mode)
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f promptenchanter2
docker-compose -f docker-compose.production.yml logs -f nginx2
docker-compose -f docker-compose.production.yml logs -f redis2
docker-compose -f docker-compose.production.yml logs -f certbot

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100

# Logs since 1 hour ago
docker-compose -f docker-compose.production.yml logs --since 1h
```

### Service Status
```bash
# Check all services
docker-compose -f docker-compose.production.yml ps

# Detailed status
docker-compose -f docker-compose.production.yml ps -a

# Resource usage
docker stats

# Disk usage
docker system df
```

### Health Checks
```bash
# Application health
curl https://yourdomain.com/health
curl -k https://localhost/health  # From server

# Redis health
docker-compose -f docker-compose.production.yml exec redis2 redis-cli ping

# Nginx config test
docker-compose -f docker-compose.production.yml exec nginx2 nginx -t

# Check all container health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## 🔧 Maintenance Commands

### Update Application
```bash
# 1. Pull latest code
git pull origin main

# 2. Stop services
./stop-production.sh

# 3. Rebuild and start
./start-production.sh --build

# OR do it manually
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Reload Nginx Configuration
```bash
# After modifying nginx.prod.conf
docker-compose -f docker-compose.production.yml exec nginx2 nginx -t  # Test config
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload  # Reload
```

### Clear Redis Cache
```bash
# Connect to Redis
docker-compose -f docker-compose.production.yml exec redis2 redis-cli

# Inside Redis CLI:
# AUTH your-redis-password
# FLUSHALL  # Clear all data (use with caution!)
# EXIT
```

### Database Operations
```bash
# Access MongoDB (if using local, but you're using Atlas)
# MongoDB Atlas is managed externally

# Backup SQLite (if using as fallback)
docker-compose -f docker-compose.production.yml exec promptenchanter2 \
  cp /app/data/promptenchanter2.db /app/data/backup-$(date +%Y%m%d).db

# Copy backup to host
docker cp promptenchanter_app:/app/data/backup-$(date +%Y%m%d).db ./backups/
```

---

## 🐛 Debugging Commands

### Access Container Shell
```bash
# Application container
docker-compose -f docker-compose.production.yml exec promptenchanter2 /bin/bash

# Nginx container
docker-compose -f docker-compose.production.yml exec nginx2 /bin/sh

# Redis container
docker-compose -f docker-compose.production.yml exec redis2 /bin/sh

# As root (for troubleshooting)
docker-compose -f docker-compose.production.yml exec -u root promptenchanter2 /bin/bash
```

### Network Debugging
```bash
# Test connectivity from nginx to app
docker-compose -f docker-compose.production.yml exec nginx2 \
  wget -O- http://promptenchanter2:8000/health

# Test DNS resolution
docker-compose -f docker-compose.production.yml exec nginx2 nslookup promptenchanter2

# Check network
docker network ls
docker network inspect promptenchanter2-network
```

### File Operations
```bash
# Copy file to container
docker cp ./localfile.txt promptenchanter_app:/app/

# Copy file from container
docker cp promptenchanter_app:/app/logs/promptenchanter.log ./logs/

# View file in container
docker-compose -f docker-compose.production.yml exec promptenchanter2 cat /app/.env

# Edit file in container (not recommended, use volume mount instead)
docker-compose -f docker-compose.production.yml exec -u root promptenchanter2 vi /etc/nginx/nginx.conf
```

---

## 📦 Backup & Restore

### Backup
```bash
# Backup Redis data
docker run --rm -v promptenchanter_redis_data2:/data -v $(pwd)/backups:/backup alpine \
  tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz /data

# Backup application data
tar czf backup-app-$(date +%Y%m%d).tar.gz ./data ./logs

# Backup SSL certificates
tar czf backup-ssl-$(date +%Y%m%d).tar.gz ./certbot

# Full backup
tar czf backup-full-$(date +%Y%m%d).tar.gz \
  ./data ./logs ./certbot .env docker-compose.production.yml nginx.prod.conf
```

### Restore
```bash
# Restore Redis data
docker run --rm -v promptenchanter_redis_data2:/data -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/redis-backup-YYYYMMDD.tar.gz -C /

# Restore application data
tar xzf backup-app-YYYYMMDD.tar.gz

# Restore SSL certificates
tar xzf backup-ssl-YYYYMMDD.tar.gz
```

---

## 🧹 Cleanup Commands

### Clean Docker Resources
```bash
# Remove stopped containers
docker-compose -f docker-compose.production.yml rm -f

# Remove unused images
docker image prune -a

# Remove unused volumes (CAUTION: loses data)
docker volume prune

# Full cleanup (CAUTION: removes everything)
docker system prune -a --volumes

# Clean build cache
docker builder prune -a
```

### Clean Logs
```bash
# Clear application logs (careful!)
> ./logs/promptenchanter.log

# Clear Docker logs for a service
docker-compose -f docker-compose.production.yml exec promptenchanter2 \
  truncate -s 0 /var/log/nginx/access.log
```

---

## 🔍 Testing Commands

### API Testing
```bash
# Test health endpoint
curl https://yourdomain.com/health

# Test API (replace with your API key)
curl -H "X-API-Key: your-api-key" https://yourdomain.com/v1/prompt/

# Test with verbose output
curl -v https://yourdomain.com/docs

# Test HTTP to HTTPS redirect
curl -I http://yourdomain.com
```

### SSL Testing
```bash
# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check certificate chain
curl -vI https://yourdomain.com 2>&1 | grep -i certificate

# Test HTTP/2
curl -I --http2 https://yourdomain.com

# External SSL test (browser)
# https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

### Performance Testing
```bash
# Simple load test (install apache2-utils)
ab -n 1000 -c 10 https://yourdomain.com/health

# Monitor resource usage during test
docker stats
```

---

## 📈 Scaling Commands

### Horizontal Scaling
```bash
# Scale application to 3 instances
docker-compose -f docker-compose.production.yml up -d --scale promptenchanter2=3

# Scale back to 1
docker-compose -f docker-compose.production.yml up -d --scale promptenchanter2=1

# Note: Nginx will load balance across instances
```

### Resource Adjustment
```bash
# Edit docker-compose.production.yml to change resource limits
vim docker-compose.production.yml

# Apply changes
docker-compose -f docker-compose.production.yml up -d
```

---

## 🚨 Emergency Commands

### Quick Restart
```bash
# Restart everything
docker-compose -f docker-compose.production.yml restart

# Force recreate containers
docker-compose -f docker-compose.production.yml up -d --force-recreate
```

### Rollback
```bash
# Rollback to previous git commit
git log --oneline  # Find commit hash
git checkout <commit-hash>

# Rebuild and restart
./stop-production.sh
./start-production.sh --build
```

### Service Recovery
```bash
# If a service is unhealthy, restart it
docker-compose -f docker-compose.production.yml restart <service-name>

# If nginx won't start, check config
docker-compose -f docker-compose.production.yml exec nginx2 nginx -t

# If app won't start, check logs
docker-compose -f docker-compose.production.yml logs promptenchanter2

# Nuclear option: full restart
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

---

## 📋 Common Workflows

### Daily Operations
```bash
# Check status
docker-compose -f docker-compose.production.yml ps

# View recent logs
docker-compose -f docker-compose.production.yml logs --tail=50 -f

# Check disk usage
df -h
docker system df
```

### Weekly Maintenance
```bash
# Check certificate expiry
docker-compose -f docker-compose.production.yml exec certbot certbot certificates

# Review logs for errors
docker-compose -f docker-compose.production.yml logs --since 7d | grep -i error

# Backup data
./backup-all.sh  # Create this script based on backup commands above
```

### Monthly Tasks
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker resources
docker system prune -a

# Review and optimize nginx config
vim nginx.prod.conf

# Check security updates
docker-compose -f docker-compose.production.yml pull
```

---

## 🔗 Useful One-Liners

```bash
# Check all service health status
docker-compose -f docker-compose.production.yml ps --format json | jq -r '.[] | "\(.Service): \(.Health)"'

# Find containers using most memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | sort -k 2 -h

# Count requests in nginx logs (last hour)
docker-compose -f docker-compose.production.yml exec nginx2 \
  awk -v date="$(date -d '1 hour ago' '+%d/%b/%Y:%H')" '$4 > "["date' /var/log/nginx/access.log | wc -l

# Monitor certificate expiry days
docker-compose -f docker-compose.production.yml exec certbot \
  certbot certificates 2>/dev/null | grep -i "expiry date" | head -1

# Quick service restart with logs
docker-compose -f docker-compose.production.yml restart && \
docker-compose -f docker-compose.production.yml logs -f --tail=50
```

---

## 💡 Tips

1. **Always test nginx config** before reloading: `nginx -t`
2. **Use `--tail` flag** to limit log output: `logs --tail=100`
3. **Monitor resources** during peak times: `docker stats`
4. **Keep backups** before major updates
5. **Test in staging** before production changes (use `STAGING=1`)
6. **Check logs regularly** for errors and warnings
7. **Document changes** to configs in git commits
8. **Use health checks** to ensure services are working

---

For more information, see:
- [PRODUCTION_README.md](PRODUCTION_README.md) - Comprehensive guide
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment steps
- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - System architecture
