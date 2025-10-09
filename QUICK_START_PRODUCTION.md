# PromptEnchanter - Production Quick Start Guide

## 🚀 Get Running in 3 Steps

### Step 1: Configure Environment (2 minutes)

Edit `.env` file and update these critical values:

```bash
# Your domain and email
DOMAIN=yourdomain.com
CERTBOT_EMAIL=admin@yourdomain.com

# Security (MUST CHANGE!)
SECRET_KEY=your-random-secret-key-minimum-32-characters
REDIS_PASSWORD=your-strong-redis-password

# Admin password (MUST CHANGE!)
DEFAULT_ADMIN_PASSWORD=YourStrongPassword123!
```

### Step 2: Initialize SSL Certificates (5 minutes)

```bash
chmod +x *.sh
./init-letsencrypt.sh
```

This will automatically:
- ✅ Set up Let's Encrypt SSL certificates
- ✅ Configure nginx for HTTPS
- ✅ Start all services

### Step 3: Access Your Application

Your app is now live at:
- 🌐 **HTTPS**: `https://yourdomain.com`
- 📚 **API Docs**: `https://yourdomain.com/docs`
- ❤️ **Health**: `https://yourdomain.com/health`

---

## 📋 Common Commands

```bash
# Start production
./start-production.sh

# Stop production
./stop-production.sh

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Check status
docker-compose -f docker-compose.production.yml ps

# Renew SSL (automatic, but can be manual)
./renew-certificates.sh
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `.env` | **Your configuration** (update domain, passwords) |
| `docker-compose.production.yml` | Production services definition |
| `nginx.prod.conf` | Nginx/SSL configuration |
| `init-letsencrypt.sh` | SSL certificate setup |
| `start-production.sh` | Start all services |
| `stop-production.sh` | Stop all services |
| `renew-certificates.sh` | Manual SSL renewal |

---

## 📚 Full Documentation

- **[PRODUCTION_README.md](PRODUCTION_README.md)** - Comprehensive guide and reference
- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Detailed deployment instructions
- **[DOCKER_SETUP_SUMMARY.md](DOCKER_SETUP_SUMMARY.md)** - Technical implementation details

---

## ✅ Pre-Deployment Checklist

- [ ] Domain DNS pointing to server IP
- [ ] Ports 80 and 443 open in firewall
- [ ] Docker and Docker Compose installed
- [ ] `.env` file configured with your values
- [ ] All default passwords changed
- [ ] `chmod +x *.sh` executed

---

## 🆘 Quick Troubleshooting

### SSL not working?
```bash
# Verify DNS
nslookup yourdomain.com

# Re-initialize SSL
./init-letsencrypt.sh
```

### Services not starting?
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Verify .env configuration
cat .env | grep -E "DOMAIN|CERTBOT_EMAIL"
```

### Need to update?
```bash
git pull
./stop-production.sh
./start-production.sh --build
```

---

## 🔐 Security Reminders

1. ✅ Change `SECRET_KEY` in `.env`
2. ✅ Change `DEFAULT_ADMIN_PASSWORD` in `.env`
3. ✅ Set strong `REDIS_PASSWORD` in `.env`
4. ✅ Use a real domain (not localhost)
5. ✅ Keep certificates auto-renewed (already configured)

---

**🎉 That's it! Your production deployment is complete!**

For detailed information, see [PRODUCTION_README.md](PRODUCTION_README.md)
