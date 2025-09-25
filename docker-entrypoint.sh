#!/bin/bash
set -e

# PromptEnchanter Docker Entrypoint Script
# This script handles initialization and startup of the PromptEnchanter application

echo "🚀 Starting PromptEnchanter Docker Container..."

# Create required directories
echo "📁 Creating required directories..."
mkdir -p /app/logs /app/data

# Set correct permissions
echo "🔧 Setting permissions..."
chown -R appuser:appuser /app/logs /app/data

# Wait for dependencies
echo "⏳ Waiting for dependencies..."

# Wait for Redis
if [ ! -z "$REDIS_URL" ]; then
    echo "🔄 Waiting for Redis..."
    until redis-cli -u "$REDIS_URL" ping 2>/dev/null; do
        echo "Redis is unavailable - sleeping"
        sleep 2
    done
    echo "✅ Redis is ready!"
fi

# Wait for Database (if PostgreSQL)
if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "🔄 Waiting for PostgreSQL..."
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "✅ PostgreSQL is ready!"
fi

# Initialize database
echo "🗄️ Initializing database..."
cd /app
python -c "
import asyncio
from app.database.database import init_database

async def init():
    try:
        await init_database()
        print('✅ Database initialized successfully')
    except Exception as e:
        print(f'❌ Database initialization failed: {e}')
        exit(1)

asyncio.run(init())
"

# Create admin user if environment variables are provided
if [ ! -z "$ADMIN_USERNAME" ] && [ ! -z "$ADMIN_PASSWORD" ]; then
    echo "👤 Creating admin user..."
    python -c "
import asyncio
from app.services.admin_service import admin_service
from app.database.database import get_db_session

async def create_admin():
    try:
        async for session in get_db_session():
            result = await admin_service.create_admin(
                session=session,
                username='$ADMIN_USERNAME',
                name='$ADMIN_NAME',
                email='$ADMIN_EMAIL',
                password='$ADMIN_PASSWORD',
                is_super_admin=True
            )
            print('✅ Admin user created successfully')
            break
    except Exception as e:
        print(f'⚠️ Admin user creation failed (may already exist): {e}')

asyncio.run(create_admin())
" || echo "⚠️ Admin user creation skipped (may already exist)"
fi

# Run any additional setup scripts
if [ -d "/app/scripts/docker-init" ]; then
    echo "🔧 Running additional setup scripts..."
    for script in /app/scripts/docker-init/*.sh; do
        if [ -x "$script" ]; then
            echo "Running $script..."
            "$script"
        fi
    done
fi

echo "✅ PromptEnchanter initialization complete!"

# Start the application
echo "🌟 Starting PromptEnchanter application..."

# Switch to appuser and start the application
exec gosu appuser "$@"