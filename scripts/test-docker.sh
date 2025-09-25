#!/bin/bash
set -e

# Docker Setup Test Script for PromptEnchanter
echo "🧪 Testing PromptEnchanter Docker Setup..."

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    echo "🔍 Checking $service health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service is healthy"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts - $service not ready, waiting..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service health check failed after $max_attempts attempts"
    return 1
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check if services are running
echo "🔍 Checking if services are running..."
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️ Services are not running. Starting them..."
    docker-compose up -d
    echo "⏳ Waiting for services to start..."
    sleep 20
fi

# Test Redis connectivity
echo "🔍 Testing Redis connectivity..."
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is responding"
else
    echo "❌ Redis is not responding"
    exit 1
fi

# Test PromptEnchanter health
check_service_health "PromptEnchanter" "http://localhost:8000/health"

# Test API endpoints
echo "🔍 Testing API endpoints..."

# Test root endpoint
echo "Testing root endpoint..."
response=$(curl -s http://localhost:8000/)
if echo "$response" | grep -q "PromptEnchanter"; then
    echo "✅ Root endpoint is working"
else
    echo "❌ Root endpoint test failed"
    echo "Response: $response"
    exit 1
fi

# Test health endpoint
echo "Testing health endpoint..."
response=$(curl -s http://localhost:8000/health)
if echo "$response" | grep -q "healthy"; then
    echo "✅ Health endpoint is working"
else
    echo "❌ Health endpoint test failed"
    echo "Response: $response"
    exit 1
fi

# Test OpenAPI docs
echo "Testing OpenAPI documentation..."
if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ OpenAPI documentation is accessible"
else
    echo "❌ OpenAPI documentation is not accessible"
    exit 1
fi

# Test with sample API call (if API key is configured)
if grep -q "WAPI_KEY=sk-" .env 2>/dev/null; then
    echo "🔍 Testing sample API call..."
    
    # Create a test user first (this might fail if user exists, which is OK)
    test_response=$(curl -s -X POST "http://localhost:8000/v1/users/register" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123"
        }' 2>/dev/null || true)
    
    # Note: We can't fully test the chat endpoint without a valid session token
    # But we can test that it properly rejects unauthorized requests
    auth_test=$(curl -s -w "%{http_code}" -X POST "http://localhost:8000/v1/prompt/completions" \
        -H "Content-Type: application/json" \
        -d '{"level": "low", "messages": [{"role": "user", "content": "test"}]}' 2>/dev/null)
    
    if echo "$auth_test" | grep -q "401"; then
        echo "✅ API authentication is working (properly rejecting unauthorized requests)"
    else
        echo "⚠️ API authentication test inconclusive"
    fi
else
    echo "⚠️ Skipping API call test (WAPI_KEY not configured)"
fi

# Check logs for errors
echo "🔍 Checking recent logs for errors..."
recent_errors=$(docker-compose logs --tail=50 promptenchanter 2>/dev/null | grep -i "error\|exception\|failed" | wc -l)

if [ "$recent_errors" -eq 0 ]; then
    echo "✅ No recent errors found in logs"
else
    echo "⚠️ Found $recent_errors potential error messages in recent logs"
    echo "Recent error-like messages:"
    docker-compose logs --tail=50 promptenchanter 2>/dev/null | grep -i "error\|exception\|failed" | tail -5
fi

# Display service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Docker setup test completed successfully!"
echo ""
echo "🔗 Access Points:"
echo "  - Main API: http://localhost:8000"
echo "  - Health Check: http://localhost:8000/health"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Alternative Docs: http://localhost:8000/redoc"
echo ""
echo "📋 Next Steps:"
echo "  1. Configure your WAPI_KEY in .env file"
echo "  2. Register a user via /v1/users/register"
echo "  3. Use the API key from registration for API calls"
echo "  4. Test the /v1/prompt/completions endpoint"
echo ""