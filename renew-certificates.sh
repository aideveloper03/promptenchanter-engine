#!/bin/bash

# PromptEnchanter - SSL Certificate Renewal Script
# This script manually renews SSL certificates and reloads nginx
# 
# Usage: ./renew-certificates.sh
#
# Note: Certificates are automatically renewed by the certbot service every 12 hours
# This script is only needed for manual renewal or troubleshooting

set -e

echo "🔐 PromptEnchanter - Manual SSL Certificate Renewal"
echo "===================================================="
echo ""

# Check if docker-compose is running
if ! docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo "❌ Error: Services are not running"
    echo "Please start services first: docker-compose -f docker-compose.production.yml up -d"
    exit 1
fi

# Check current certificate status
echo "📋 Current certificate status:"
docker-compose -f docker-compose.production.yml exec certbot certbot certificates
echo ""

# Check expiration
echo "🕐 Checking certificate expiration..."
docker-compose -f docker-compose.production.yml exec certbot certbot certificates | grep "Expiry Date" || true
echo ""

# Ask for confirmation
read -p "Do you want to renew certificates now? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Certificate renewal cancelled."
    exit 0
fi

# Attempt renewal
echo "🔄 Attempting certificate renewal..."
if docker-compose -f docker-compose.production.yml exec certbot certbot renew --force-renewal; then
    echo "✅ Certificates renewed successfully!"
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    if docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload; then
        echo "✅ Nginx reloaded successfully!"
    else
        echo "⚠️  Warning: Failed to reload nginx. Trying restart..."
        docker-compose -f docker-compose.production.yml restart nginx2
        echo "✅ Nginx restarted!"
    fi
    
    # Show new certificate info
    echo ""
    echo "📜 Updated certificate information:"
    docker-compose -f docker-compose.production.yml exec certbot certbot certificates
    
    echo ""
    echo "===================================================="
    echo "✅ Certificate renewal completed successfully!"
    echo "===================================================="
    echo ""
    echo "Your SSL certificates have been renewed and nginx has been reloaded."
    echo "Next automatic renewal will occur within 12 hours."
    echo ""
else
    echo "❌ Certificate renewal failed!"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check certbot logs: docker-compose -f docker-compose.production.yml logs certbot"
    echo "2. Verify domain is pointing to this server: nslookup \$DOMAIN"
    echo "3. Ensure ports 80 and 443 are open: sudo ufw status"
    echo "4. Try re-initializing: ./init-letsencrypt.sh"
    echo ""
    exit 1
fi
