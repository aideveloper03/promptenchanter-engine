#!/bin/bash
set -e

# Production Setup Script for PromptEnchanter
echo "🚀 Setting up PromptEnchanter for Production..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    exit 1
fi

# Check if Docker and Docker Compose are installed
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

echo "✅ Docker and Docker Compose are installed"

# Create required directories
echo "📁 Creating production directories..."
mkdir -p logs data ssl secrets

# Set secure permissions
chmod 700 secrets
chmod 755 logs data ssl

# Check for environment file
if [ ! -f ".env" ]; then
    echo "⚠️ No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your production configuration"
    echo "❗ IMPORTANT: Change the SECRET_KEY and WAPI_KEY values!"
    read -p "Press enter when you have configured the .env file..."
fi

# Generate secrets if they don't exist
if [ ! -f "secrets/postgres_password.txt" ]; then
    echo "🔐 Generating PostgreSQL password..."
    openssl rand -base64 32 > secrets/postgres_password.txt
    chmod 600 secrets/postgres_password.txt
    echo "✅ PostgreSQL password generated"
fi

# Check SSL certificates
if [ ! -f "ssl/fullchain.pem" ] || [ ! -f "ssl/privkey.pem" ]; then
    echo "⚠️ SSL certificates not found in ssl/ directory"
    echo "For production, you need:"
    echo "  - ssl/fullchain.pem (SSL certificate)"
    echo "  - ssl/privkey.pem (SSL private key)"
    echo ""
    echo "You can:"
    echo "  1. Use Let's Encrypt: certbot certonly --standalone -d yourdomain.com"
    echo "  2. Copy your existing certificates to the ssl/ directory"
    echo ""
    read -p "Do you want to continue without SSL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please set up SSL certificates and run this script again"
        exit 1
    fi
fi

# Validate environment configuration
echo "🔍 Validating configuration..."

# Check required variables
required_vars=("WAPI_URL" "WAPI_KEY" "SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=.*change.*" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ The following required variables are missing or have default values in .env:"
    printf ' - %s\n' "${missing_vars[@]}"
    echo "Please configure these variables before proceeding"
    exit 1
fi

echo "✅ Configuration validated"

# Build and start services
echo "🏗️ Building and starting production services..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ PromptEnchanter is healthy"
else
    echo "❌ PromptEnchanter health check failed"
    echo "📋 Checking logs:"
    docker-compose logs --tail=20 promptenchanter
    exit 1
fi

echo ""
echo "🎉 Production setup complete!"
echo ""
echo "📊 Service URLs:"
echo "  - API: http://localhost:8000"
echo "  - Health: http://localhost:8000/health"
echo "  - Documentation: http://localhost:8000/docs"
echo ""
echo "🔧 Management Commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Update: docker-compose pull && docker-compose up -d"
echo ""
echo "⚠️ Security Notes:"
echo "  - Change default passwords"
echo "  - Configure SSL certificates"
echo "  - Set up firewall rules"
echo "  - Enable monitoring"
echo ""