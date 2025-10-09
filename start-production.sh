#!/bin/bash

# PromptEnchanter - Production Startup Script
# This script provides a convenient way to start the application in production mode
#
# Usage: ./start-production.sh [options]
#
# Options:
#   --build     Rebuild containers before starting
#   --logs      Show logs after starting
#   --help      Show this help message

set -e

COMPOSE_FILE="docker-compose.production.yml"
BUILD_FLAG=""
SHOW_LOGS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            echo "PromptEnchanter Production Startup Script"
            echo ""
            echo "Usage: ./start-production.sh [options]"
            echo ""
            echo "Options:"
            echo "  --build     Rebuild containers before starting"
            echo "  --logs      Show logs after starting"
            echo "  --help      Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 PromptEnchanter - Production Startup"
echo "======================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with required configuration"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
REQUIRED_VARS=("DOMAIN" "CERTBOT_EMAIL" "SECRET_KEY" "MONGODB_URL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please set these variables in your .env file"
    exit 1
fi

# Check if SSL certificates exist
if [ ! -d "./certbot/conf/live/$DOMAIN" ]; then
    echo "⚠️  Warning: SSL certificates not found for $DOMAIN"
    echo ""
    echo "Would you like to initialize SSL certificates now?"
    read -p "Run ./init-letsencrypt.sh? (y/N) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./init-letsencrypt.sh
    else
        echo "❌ Cannot start without SSL certificates"
        echo "Please run: ./init-letsencrypt.sh"
        exit 1
    fi
fi

# Stop any running services
echo "🛑 Stopping any running services..."
docker-compose -f $COMPOSE_FILE down 2>/dev/null || true

# Build if requested
if [ -n "$BUILD_FLAG" ]; then
    echo "🔨 Building containers..."
    docker-compose -f $COMPOSE_FILE build --no-cache
fi

# Start services
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f $COMPOSE_FILE ps

# Test endpoints
echo ""
echo "🔍 Testing endpoints..."

# Test health endpoint
if curl -s -f -k "https://$DOMAIN/health" > /dev/null 2>&1; then
    echo "   ✅ HTTPS health check: OK"
else
    echo "   ⚠️  HTTPS health check: Failed (may take a moment to start)"
fi

echo ""
echo "======================================="
echo "✅ PromptEnchanter Started Successfully!"
echo "======================================="
echo ""
echo "🌐 Access your application:"
echo "   • HTTPS: https://$DOMAIN"
echo "   • API Docs: https://$DOMAIN/docs"
echo "   • ReDoc: https://$DOMAIN/redoc"
echo ""
echo "📊 Management commands:"
echo "   • View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "   • Stop services: docker-compose -f $COMPOSE_FILE down"
echo "   • Restart: docker-compose -f $COMPOSE_FILE restart"
echo "   • Renew SSL: ./renew-certificates.sh"
echo ""

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo "📋 Showing logs (Ctrl+C to exit)..."
    echo ""
    docker-compose -f $COMPOSE_FILE logs -f
fi
