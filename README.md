# PromptEnchanter

**PromptEnchanter** is an enterprise-grade AI service that enhances user prompts by adding researched content and applying various prompt engineering methodologies. It serves as an intelligent proxy to AI APIs, enriching prompts with contextual information and structured reasoning approaches.

## 🚀 Features

### Core Capabilities
- **AI API Proxying**: Seamlessly forwards enhanced requests to external AI APIs (WAPI)
- **Prompt Engineering Styles**: Support for multiple prompt engineering methodologies
- **AI Deep Research**: Internet-powered research with multi-source content synthesis
- **Batch Processing**: Efficient processing of multiple prompts with parallel execution
- **Enterprise Security**: Comprehensive security with encryption, firewall, and audit logging
- **Intelligent Caching**: Redis-based caching for responses and research results

### 🆕 User Management System
- **User Registration & Authentication**: Secure user accounts with session management
- **API Key Management**: Unique API keys for each user with regeneration capabilities
- **Credit System**: Conversation credits with automatic daily resets
- **Admin Panel**: Full administrative control over users and system
- **Support Staff System**: Role-based support staff (new/support/advanced levels)
- **Security Features**: IP whitelisting, firewall, failed attempt tracking
- **Message Logging**: High-performance batch logging of all conversations
- **Data Encryption**: Sensitive data encrypted at rest and in transit

### Prompt Engineering Styles (r_type)
- **BPE** (`bpe`): Basic Prompt Engineering - Clear, structured responses
- **BCOT** (`bcot`): Basic Chain of Thoughts - Step-by-step reasoning
- **HCOT** (`hcot`): High Chain of Thoughts - Advanced multi-angle analysis
- **ReAct** (`react`): Reasoning + Action - Observe, Think, Act, Reflect methodology
- **ToT** (`tot`): Tree of Thoughts - Multiple thought branches with evaluation

### AI Deep Research
- Automatic topic identification and research planning
- Multi-source web search and content extraction
- AI-powered content synthesis and classification
- Configurable research depth (basic, medium, high)
- Intelligent caching of research results

## 📋 Requirements

- Python 3.8+
- Redis (optional, falls back to memory cache)
- Internet connection for research functionality

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd promptenchanter
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database and create admin**
   ```bash
   # Create the first admin user
   python scripts/create_admin.py
   ```

5. **Start Redis (optional but recommended)**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:alpine
   
   # Or install locally
   # Ubuntu/Debian: sudo apt-get install redis-server
   # macOS: brew install redis
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# PromptEnchanter Configuration
API_KEY=sk-78912903  # Legacy - for backward compatibility
WAPI_URL=https://api-server02.webraft.in/v1/chat/completions
WAPI_KEY=sk-Xf6CNfK8A4bCmoRAE8pBRCKyEJrJKigjlVlqCtf07AZmpije

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./promptenchanter.db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here-change-this-in-production
ALGORITHM=HS256

# User Management
USER_REGISTRATION_ENABLED=true
EMAIL_VERIFICATION_ENABLED=false
IP_WHITELIST_ENABLED=false
FIREWALL_ENABLED=true

# Session Settings
SESSION_DURATION_HOURS=24
REFRESH_TOKEN_DURATION_DAYS=30

# Message Logging
MESSAGE_LOGGING_ENABLED=true
MESSAGE_BATCH_SIZE=50
MESSAGE_FLUSH_INTERVAL_SECONDS=600

# Credit Management
AUTO_CREDIT_RESET_ENABLED=true
DAILY_USAGE_RESET_HOUR=0

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# Cache Settings
CACHE_TTL_SECONDS=3600
RESEARCH_CACHE_TTL_SECONDS=86400

# Concurrency Settings
MAX_CONCURRENT_REQUESTS=50
BATCH_MAX_PARALLEL_TASKS=10
```

### Model Level Mapping

| Level | Model |
|-------|-------|
| `low` | gpt-4o-mini |
| `medium` | gpt-4o |
| `high` | o3-mini |
| `ultra` | gpt-5 |

## 🚀 Running the Service

### Development
```bash
python main.py
```

### Production
```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker
```bash
# Build image
docker build -t promptenchanter .

# Run container
docker run -d -p 8000:8000 --env-file .env promptenchanter
```

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Authentication

#### User Registration & Login

New users must register and obtain an API key:

```bash
# Register new user
curl -X POST "https://api.promptenchanter.net/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "name": "John Doe", 
    "email": "john@example.com",
    "password": "SecurePass123"
  }'

# Response includes API key
{
  "api_key": "pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y",
  "user_id": 1,
  "username": "johndoe"
}
```

#### API Authentication

All API endpoints require Bearer token authentication with user API key:

```bash
Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y
```

## 🔧 API Usage Examples

### 1. Basic Chat Completion

```bash
curl https://api.promptenchanter.net/v1/prompt/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -d '{
    "level": "medium",
    "messages": [
      {
        "role": "user",
        "content": "Create a code for AI systems."
      }
    ],
    "r_type": "bpe",
    "temperature": 0.7
  }'
```

### 2. Chat Completion with AI Research

```bash
curl https://api.promptenchanter.net/v1/prompt/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -d '{
    "level": "high",
    "messages": [
      {
        "role": "user",
        "content": "Explain the latest developments in quantum computing."
      }
    ],
    "r_type": "hcot",
    "ai_research": true,
    "research_depth": "high",
    "temperature": 0.5
  }'
```

### 3. Batch Processing

```bash
curl https://api.promptenchanter.net/v1/batch/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -d '{
    "batch": [
      {
        "prompt": "Explain machine learning basics",
        "r_type": "bpe",
        "temperature": 0.7
      },
      {
        "prompt": "Create a React component for user profile",
        "r_type": "react",
        "max_tokens": 1000
      }
    ],
    "level": "medium",
    "enable_research": true,
    "parallel": true
  }'
```

### 4. Admin Operations

```bash
# Health Check
curl https://api.promptenchanter.net/v1/admin/health \
  -H "Authorization: Bearer sk-78912903"

# Get System Prompts
curl https://api.promptenchanter.net/v1/admin/system-prompts \
  -H "Authorization: Bearer sk-78912903"

# Update System Prompt
curl -X PUT https://api.promptenchanter.net/v1/admin/system-prompts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -d '{
    "r_type": "custom",
    "prompt": "You are a specialized AI assistant..."
  }'

# Clear Cache
curl -X DELETE https://api.promptenchanter.net/v1/admin/cache \
  -H "Authorization: Bearer sk-78912903"
```

## 🏗️ Architecture

### Core Components

1. **API Layer** (`app/api/`)
   - FastAPI-based REST API
   - Authentication and rate limiting middleware
   - Request/response logging

2. **Services** (`app/services/`)
   - `prompt_service.py`: Core prompt enhancement logic
   - `wapi_client.py`: External AI API client with retry logic
   - `research_service.py`: AI-powered research with web search
   - `batch_service.py`: Batch processing with concurrency control

3. **Models** (`app/models/`)
   - Pydantic models for request/response validation
   - Type safety and automatic documentation

4. **Utils** (`app/utils/`)
   - Caching (Redis + memory fallback)
   - Security and authentication
   - Structured logging

### Request Flow

1. **Authentication**: Verify API key
2. **Rate Limiting**: Check request limits
3. **Enhancement**: Apply r_type system prompts
4. **Research** (if enabled): Conduct AI research
5. **Proxy**: Forward to WAPI with modifications
6. **Caching**: Store results for future use
7. **Response**: Return enhanced response

### Research Process

1. **Topic Analysis**: AI identifies research topics
2. **Web Search**: Multi-source search using DuckDuckGo
3. **Content Extraction**: Parse and clean web content
4. **AI Synthesis**: Combine sources into coherent research
5. **Integration**: Add research to user prompt

## 🔒 Security Features

- **API Key Authentication**: Bearer token validation
- **Rate Limiting**: Configurable per-minute limits with burst support
- **Input Sanitization**: XSS and injection prevention
- **Request Logging**: Comprehensive audit trails
- **Error Handling**: Secure error responses without information leakage

## 📊 Monitoring & Logging

### Structured Logging
- JSON-formatted logs in production
- Console-friendly logs in development
- Request tracing with unique IDs
- Performance metrics and error tracking

### Health Checks
- Service health endpoint
- External API connectivity checks
- Redis connection monitoring
- System statistics and metrics

## 🚀 Performance Optimization

### Caching Strategy
- **Response Caching**: Cache API responses by request hash
- **Research Caching**: Long-term cache for research results
- **Redis + Memory**: Fallback caching system

### Concurrency
- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient HTTP client management
- **Semaphore Limiting**: Controlled concurrent requests
- **Batch Parallelization**: Configurable parallel task execution

## 🛡️ Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Considerations
- Set `DEBUG=false` in production
- Use strong `SECRET_KEY`
- Configure appropriate `CORS` settings
- Set up proper logging aggregation
- Monitor Redis memory usage
- Configure firewall rules

### Scaling
- Use multiple workers with Gunicorn
- Deploy behind load balancer (nginx, HAProxy)
- Scale Redis with clustering if needed
- Monitor and adjust rate limits
- Consider CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the logs for error details
- Ensure proper configuration in `.env`
- Verify Redis connectivity
- Check WAPI endpoint accessibility

## 📚 Documentation

- **[User Management Guide](docs/USER_MANAGEMENT_GUIDE.md)** - Comprehensive guide to the user management system
- **[API Guide](docs/API_GUIDE.md)** - Detailed API documentation
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions

## 🆕 What's New in v2.0.0

### User Management System
- **Complete user registration and authentication system**
- **API key management with secure generation and regeneration**
- **Credit-based usage system with automatic daily resets**
- **Session management with refresh tokens**

### Admin & Support Features
- **Full admin panel for user and system management**
- **Role-based support staff system (new/support/advanced levels)**
- **Comprehensive user profile management**
- **Account deletion with data archiving**

### Security Enhancements
- **Advanced firewall with IP-based blocking and whitelisting**
- **Data encryption for sensitive information**
- **Failed attempt tracking and account lockouts**
- **Comprehensive security event logging**

### Performance & Monitoring
- **High-performance message logging with batch processing**
- **API usage tracking and analytics**
- **System health monitoring**
- **Automated credit reset service**

## 🔄 Version History

### v2.0.0
- **🆕 Complete user management system**
- **🆕 Admin panel and support staff roles**
- **🆕 Advanced security features (firewall, encryption, IP whitelisting)**
- **🆕 High-performance message logging**
- **🆕 Credit system with automatic resets**
- **🆕 API key authentication for all endpoints**
- Enhanced documentation and setup scripts

### v1.0.0
- Initial release
- Core prompt enhancement features
- AI research integration
- Batch processing
- Enterprise security features
- Comprehensive documentation