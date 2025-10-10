#!/bin/bash

# PromptEnchanter - Let's Encrypt SSL Certificate Initialization Script
# This script initializes SSL certificates using Certbot and Let's Encrypt
# 
# Usage: ./init-letsencrypt.sh
# 
# Prerequisites:
# - Docker and Docker Compose installed
# - Domain name configured and pointing to this server
# - Ports 80 and 443 open in firewall

set -e

echo "🔐 PromptEnchanter - Let's Encrypt SSL Certificate Initialization"
echo "================================================================="
echo ""

# Load environment variables using a safe method that handles JSON values
if [ -f .env ]; then
    set -a
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^[[:space:]]*# ]] && [[ -n "$key" ]]; then
            # Remove leading/trailing whitespace from key
            key=$(echo "$key" | xargs)
            # Only export if it's a valid variable name
            if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
                export "$key=$value"
            fi
        fi
    done < .env
    set +a
else
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with DOMAIN and CERTBOT_EMAIL variables"
    exit 1
fi

# Check required variables
if [ -z "$DOMAIN" ]; then
    echo "❌ Error: DOMAIN not set in .env file"
    echo "Please set DOMAIN=yourdomain.com in your .env file"
    exit 1
fi

if [ -z "$CERTBOT_EMAIL" ]; then
    echo "❌ Error: CERTBOT_EMAIL not set in .env file"
    echo "Please set CERTBOT_EMAIL=your@email.com in your .env file"
    exit 1
fi

# Configuration
domains=($DOMAIN)
rsa_key_size=4096
data_path="./certbot"
email="$CERTBOT_EMAIL"
staging=${STAGING:-0} # Set to 1 for testing

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   Email: $CERTBOT_EMAIL"
echo "   Staging mode: $([ $staging -eq 1 ] && echo 'YES (testing)' || echo 'NO (production)')"
echo ""

# Create required directories
echo "📁 Creating required directories..."
mkdir -p "$data_path/conf"
mkdir -p "$data_path/www"
mkdir -p "$data_path/logs"
mkdir -p "./nginx/cache"

# Download recommended TLS parameters if they don't exist
if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
    echo "⬇️  Downloading recommended TLS parameters..."
    mkdir -p "$data_path/conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
    echo "✅ TLS parameters downloaded"
fi

# Check if certificates already exist
if [ -d "$data_path/conf/live/$DOMAIN" ]; then
    echo ""
    echo "⚠️  Existing certificates found for $DOMAIN"
    read -p "Do you want to replace them? (y/N) " decision
    if [ "$decision" != "y" ] && [ "$decision" != "Y" ]; then
        echo "Keeping existing certificates. Exiting."
        exit 0
    fi
    echo "🗑️  Removing existing certificates..."
    docker-compose -f docker-compose.production.yml run --rm --entrypoint "\
        rm -rf /etc/letsencrypt/live/$DOMAIN && \
        rm -rf /etc/letsencrypt/archive/$DOMAIN && \
        rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
fi

# Create dummy certificate for nginx to start
echo "🔧 Creating dummy certificate for $DOMAIN..."
path="/etc/letsencrypt/live/$DOMAIN"
mkdir -p "$data_path/conf/live/$DOMAIN"
docker-compose -f docker-compose.production.yml run --rm --entrypoint "\
    openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1 \
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo "✅ Dummy certificate created"

# Update nginx configuration with actual domain
echo "🔧 Updating nginx configuration with domain: $DOMAIN..."
sed -i.bak "s/your-domain/$DOMAIN/g" nginx.prod.conf
echo "✅ Nginx configuration updated"

# Start nginx with dummy certificate
echo "🚀 Starting nginx with dummy certificate..."
docker-compose -f docker-compose.production.yml up -d nginx2
echo "✅ Nginx started"

# Wait for nginx to be ready
echo "⏳ Waiting for nginx to be ready..."
sleep 5

# Delete dummy certificate
echo "🗑️  Removing dummy certificate..."
docker-compose -f docker-compose.production.yml run --rm --entrypoint "\
    rm -rf /etc/letsencrypt/live/$DOMAIN && \
    rm -rf /etc/letsencrypt/archive/$DOMAIN && \
    rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
echo "✅ Dummy certificate removed"

# Request Let's Encrypt certificate
echo "📜 Requesting Let's Encrypt certificate for $DOMAIN..."

# Set staging flag
staging_arg=""
if [ $staging -eq 1 ]; then
    staging_arg="--staging"
    echo "⚠️  Using staging server for testing"
fi

# Join domains for -d args
domain_args=""
for domain in "${domains[@]}"; do
    domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$email" in
    "") email_arg="--register-unsafely-without-email" ;;
    *) email_arg="--email $email" ;;
esac

# Request certificate
docker-compose -f docker-compose.production.yml run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal \
    --non-interactive" certbot

echo ""
echo "✅ Certificate obtained successfully!"

# Reload nginx to use the real certificate
echo "🔄 Reloading nginx to use real certificate..."
docker-compose -f docker-compose.production.yml exec nginx2 nginx -s reload
echo "✅ Nginx reloaded"

echo ""
echo "================================================================="
echo "🎉 SUCCESS! SSL certificates have been installed!"
echo "================================================================="
echo ""
echo "Your application is now accessible via HTTPS at: https://$DOMAIN"
echo ""
echo "📝 Next steps:"
echo "   1. Test your SSL configuration: https://www.ssllabs.com/ssltest/"
echo "   2. Certificates will auto-renew every 12 hours"
echo "   3. Monitor logs: docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔐 Certificate details:"
echo "   Location: $data_path/conf/live/$DOMAIN/"
echo "   Renewal: Automatic (runs every 12 hours)"
echo "   Expiry: ~90 days from now"
echo ""

if [ $staging -eq 1 ]; then
    echo "⚠️  NOTE: You used staging certificates (for testing)"
    echo "    To get production certificates, run: STAGING=0 ./init-letsencrypt.sh"
    echo ""
fi

echo "================================================================="
