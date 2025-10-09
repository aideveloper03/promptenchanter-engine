#!/bin/bash

# PromptEnchanter - Production Stop Script
# This script safely stops all production services
#
# Usage: ./stop-production.sh [options]
#
# Options:
#   --remove-volumes    Remove volumes (WARNING: deletes data!)
#   --help              Show this help message

set -e

COMPOSE_FILE="docker-compose.production.yml"
REMOVE_VOLUMES=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-volumes)
            REMOVE_VOLUMES="--volumes"
            shift
            ;;
        --help)
            echo "PromptEnchanter Production Stop Script"
            echo ""
            echo "Usage: ./stop-production.sh [options]"
            echo ""
            echo "Options:"
            echo "  --remove-volumes    Remove volumes (WARNING: deletes data!)"
            echo "  --help              Show this help message"
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

echo "🛑 PromptEnchanter - Stopping Production Services"
echo "=================================================="
echo ""

# Warn about volume removal
if [ -n "$REMOVE_VOLUMES" ]; then
    echo "⚠️  WARNING: You are about to remove all volumes!"
    echo "This will DELETE all data including:"
    echo "   • Redis cache data"
    echo "   • Application logs"
    echo "   • Any other persisted data"
    echo ""
    read -p "Are you absolutely sure? Type 'yes' to confirm: " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted. No changes made."
        exit 0
    fi
    echo ""
fi

# Show current status
echo "📊 Current service status:"
docker-compose -f $COMPOSE_FILE ps
echo ""

# Stop services
echo "🛑 Stopping services..."
docker-compose -f $COMPOSE_FILE down $REMOVE_VOLUMES

echo ""
echo "=================================================="
echo "✅ All services stopped successfully!"
echo "=================================================="
echo ""

if [ -n "$REMOVE_VOLUMES" ]; then
    echo "⚠️  All volumes have been removed"
    echo ""
fi

echo "To start services again, run: ./start-production.sh"
echo ""
