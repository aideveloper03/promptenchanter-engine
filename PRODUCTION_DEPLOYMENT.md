# PromptEnchanter Production Deployment Guide

This guide provides step-by-step instructions for deploying PromptEnchanter in a production environment with Docker and SSL/HTTPS support using Let's Encrypt certificates.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [SSL Certificate Setup](#ssl-certificate-setup)
4. [Deployment](#deployment)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)

---

## 📦 Prerequisites

### Required Software
- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Git** (for cloning the repository)

### Server Requirements
- **OS**: Ubuntu 20.04 LTS or higher (or any Linux distribution with Docker support)
- **RAM**: Minimum 2GB (4GB recommended)
- **CPU**: 2 cores minimum
- **Disk**: 20GB minimum
- **Network**: Public IP address with ports 80 and 443 accessible

### Domain Configuration
- A registered domain name
- DNS A record pointing to your server's IP address
- Firewall configured to allow ports 80 (HTTP) and 443 (HTTPS)

---

## 🚀 Server Setup

### 1. Install Docker and Docker Compose

```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Clone Repository

```bash
# Clone the repository
git clone <your-repository-url>
cd promptenchanter

# Or if you already have the code, navigate to the directory
cd /path/to/promptenchanter
```

### 3. Configure Firewall

```bash
# Allow SSH (if using UFW)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

---

## 🔐 SSL Certificate Setup

### 1. Configure Environment Variables

Edit the `.env` file and set the following required variables:

```bash
# SSL/HTTPS Configuration
DOMAIN=yourdomain.com                    # Your actual domain name
CERTBOT_EMAIL=admin@yourdomain.com       # Email for Let's Encrypt notifications

# Security (IMPORTANT: Change these in production!)
SECRET_KEY=your-super-secret-key-here-change-this
API_KEY=your-api-key-change-this
REDIS_PASSWORD=your-redis-password

# Database - Keep MongoDB settings as provided
MONGODB_URL=mongodb+srv://aideveloper03690_db_user:c0evekYI3q2EnpuY@cluster0.cptyxpt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DATABASE=promptenchanter
USE_MONGODB=true

# Admin Account (Change password!)
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=YourStrongPasswordHere!
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
```

### 2. Test SSL Setup (Optional - Staging Mode)

For testing, you can use Let's Encrypt staging servers to avoid rate limits:

```bash
# Run with staging certificates (won't show as valid in browser)
STAGING=1 ./init-letsencrypt.sh
```

### 3. Initialize SSL Certificates (Production)

```bash
# Make the script executable (if not already)
chmod +x init-letsencrypt.sh

# Run the initialization script
./init-letsencrypt.sh
```

This script will:
- Create necessary directories
- Download TLS parameters
- Create a temporary dummy certificate
- Start nginx
- Request real certificates from Let's Encrypt
- Reload nginx with the real certificates

**Note**: The script will automatically update `nginx.prod.conf` with your domain name.

---

## 🚢 Deployment

### 1. Start All Services

```bash
# Start all services in production mode
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### 2. Verify Services

```bash
# Check service status
docker-compose -f docker-compose.production.yml ps

# Expected output:
# - promptenchanter_app (running)
# - promptenchanter_redis (running)
# - promptenchanter_nginx (running)
# - promptenchanter_certbot (running)

# Test health endpoint
curl https://yourdomain.com/health

# Expected response: {"status": "healthy"}
```

### 3. Access the Application

Your application is now accessible at:
- **HTTPS**: `https://yourdomain.com`
- **API Docs**: `https://yourdomain.com/docs`
- **ReDoc**: `https://yourdomain.com/redoc`

---

## 📊 Monitoring & Maintenance

### View Logs

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f promptenchanter2
docker-compose -f docker-compose.production.yml logs -f nginx2
docker-compose -f docker-compose.production.yml logs -f redis2
docker-compose -f docker-compose.production.yml logs -f certbot
```

### Certificate Renewal

SSL certificates are **automatically renewed** every 12 hours by the Certbot service. You can also manually renew:

```bash
# Manual certificate renewal
docker-compose -f docker-compose.production.yml exec certbot certbot renew

# Reload nginx after manual renewal
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload
```

### Check Certificate Expiry

```bash
# Check certificate expiration date
docker-compose -f docker-compose.production.yml exec certbot certbot certificates
```

### Database Backup

```bash
# Backup SQLite database (if using SQLite)
docker-compose -f docker-compose.production.yml exec promptenchanter2 \
    cp /app/data/promptenchanter2.db /app/data/backup-$(date +%Y%m%d).db

# Copy backup to host
docker cp promptenchanter_app:/app/data/backup-$(date +%Y%m%d).db ./backups/

# MongoDB is already hosted on Atlas (backed up by MongoDB)
```

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Verify deployment
docker-compose -f docker-compose.production.yml ps
```

### Scale Services (Optional)

```bash
# Scale the application service (if needed)
docker-compose -f docker-compose.production.yml up -d --scale promptenchanter2=3
```

---

## 🔧 Troubleshooting

### Issue: SSL Certificate Not Working

**Symptoms**: Browser shows "Not Secure" or certificate errors

**Solutions**:
1. Verify domain DNS is correctly pointing to server:
   ```bash
   nslookup yourdomain.com
   dig yourdomain.com
   ```

2. Check certificate files exist:
   ```bash
   ls -la ./certbot/conf/live/yourdomain.com/
   ```

3. Re-run initialization:
   ```bash
   ./init-letsencrypt.sh
   ```

### Issue: Nginx Not Starting

**Symptoms**: Nginx container exits or restarts continuously

**Solutions**:
1. Check nginx configuration:
   ```bash
   docker-compose -f docker-compose.production.yml exec nginx2 nginx -t
   ```

2. Verify nginx.prod.conf has correct domain:
   ```bash
   grep "server_name" nginx.prod.conf
   ```

3. Check nginx logs:
   ```bash
   docker-compose -f docker-compose.production.yml logs nginx2
   ```

### Issue: Application Not Accessible

**Symptoms**: Cannot access application via HTTPS

**Solutions**:
1. Check firewall:
   ```bash
   sudo ufw status
   sudo iptables -L -n
   ```

2. Verify all containers are running:
   ```bash
   docker-compose -f docker-compose.production.yml ps
   ```

3. Check application logs:
   ```bash
   docker-compose -f docker-compose.production.yml logs promptenchanter2
   ```

4. Test internal connectivity:
   ```bash
   # From nginx to app
   docker-compose -f docker-compose.production.yml exec nginx2 wget -O- http://promptenchanter2:8000/health
   ```

### Issue: Rate Limit Errors

**Symptoms**: Too many requests errors (429)

**Solutions**:
1. Adjust rate limits in `nginx.prod.conf`:
   ```nginx
   limit_req_zone $binary_remote_addr zone=api:10m rate=200r/m;  # Increase rate
   ```

2. Restart nginx:
   ```bash
   docker-compose -f docker-compose.production.yml restart nginx2
   ```

### Issue: Out of Disk Space

**Symptoms**: Application errors, container crashes

**Solutions**:
1. Clean up Docker:
   ```bash
   docker system prune -a --volumes
   ```

2. Rotate logs:
   ```bash
   # Docker handles log rotation automatically with the config in docker-compose
   # But you can manually clean:
   docker-compose -f docker-compose.production.yml down
   sudo rm -rf ./logs/*
   docker-compose -f docker-compose.production.yml up -d
   ```

### Issue: Redis Connection Errors

**Symptoms**: Cache not working, session errors

**Solutions**:
1. Check Redis is running:
   ```bash
   docker-compose -f docker-compose.production.yml ps redis2
   ```

2. Test Redis connection:
   ```bash
   docker-compose -f docker-compose.production.yml exec redis2 redis-cli ping
   # Should respond: PONG
   ```

3. Check Redis password in .env matches docker-compose.production.yml

---

## 📈 Performance Optimization

### 1. Enable HTTP/2 (Already Configured)
HTTP/2 is already enabled in `nginx.prod.conf` for better performance.

### 2. Optimize Redis
```bash
# Increase Redis memory limit if needed (in docker-compose.production.yml)
# Under redis2 service, update memory limit:
#   limits:
#     memory: 1G
```

### 3. Monitor Resource Usage
```bash
# Check Docker resource usage
docker stats

# Check disk usage
df -h
du -sh ./logs ./data ./certbot
```

### 4. Database Optimization
- MongoDB Atlas automatically handles optimization
- For SQLite, regular VACUUM operations are recommended

---

## 🔒 Security Best Practices

1. **Change Default Credentials**: Update all default passwords in `.env`
2. **Enable Firewall**: Use UFW or iptables to restrict access
3. **Regular Updates**: Keep Docker and system packages updated
4. **Monitor Logs**: Regularly review application and nginx logs
5. **Backup Data**: Implement automated backup strategy
6. **SSL/TLS**: Keep certificates up to date (automatic with Certbot)
7. **Environment Variables**: Never commit `.env` to version control
8. **Rate Limiting**: Configure appropriate rate limits for your use case

---

## 📞 Support

For issues or questions:
- Check application logs: `docker-compose -f docker-compose.production.yml logs`
- Review API documentation: `https://yourdomain.com/docs`
- Check SSL configuration: `https://www.ssllabs.com/ssltest/`

---

## 📝 Quick Reference Commands

```bash
# Start services
docker-compose -f docker-compose.production.yml up -d

# Stop services
docker-compose -f docker-compose.production.yml down

# Restart services
docker-compose -f docker-compose.production.yml restart

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Check service status
docker-compose -f docker-compose.production.yml ps

# Execute command in container
docker-compose -f docker-compose.production.yml exec promptenchanter2 <command>

# Renew SSL certificates
docker-compose -f docker-compose.production.yml exec certbot certbot renew

# Reload nginx
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload

# Clean up
docker system prune -a
```

---

**✅ Your PromptEnchanter application is now production-ready with HTTPS!**
