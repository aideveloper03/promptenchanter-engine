# PromptEnchanter API Guide

This guide provides detailed information about using the PromptEnchanter API.

## Authentication

All API requests require authentication using a Bearer token with your API key:

```http
Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y
```

**Note**: API keys have the format `pe-` followed by 32 alphanumeric characters. You obtain your API key when registering an account.

## Base URL

```
https://api.promptenchanter.net/v1
```

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prompt/completions` | POST | Enhanced chat completion |
| `/batch/process` | POST | Batch prompt processing |
| `/users/register` | POST | Register new user account |
| `/users/login` | POST | User authentication |
| `/users/profile` | GET | Get user profile |
| `/users/profile` | PUT | Update user profile |
| `/users/api-key` | GET | Get user API key |
| `/users/api-key/regenerate` | POST | Regenerate API key |
| `/users/logout` | POST | User logout |
| `/admin/health` | GET | Health check |
| `/admin/system-prompts` | GET | Get system prompts |
| `/admin/system-prompts` | PUT | Update system prompt |
| `/admin/cache` | DELETE | Clear cache |
| `/admin/stats` | GET | System statistics |

## Chat Completion API

### Endpoint
```
POST /v1/prompt/completions
```

### Request Body

```json
{
  "level": "medium",
  "messages": [
    {
      "role": "user",
      "content": "Your prompt here"
    }
  ],
  "r_type": "bpe",
  "ai_research": false,
  "research_depth": "basic",
  "temperature": 0.7,
  "max_tokens": null,
  "top_p": null,
  "frequency_penalty": null,
  "presence_penalty": null,
  "stop": null
}
```

### Parameters

#### Required Parameters
- **level** (string): Model level selection
  - `"low"` → gpt-4o-mini
  - `"medium"` → gpt-4o
  - `"high"` → o3-mini
  - `"ultra"` → gpt-5

- **messages** (array): Conversation messages
  - **role** (string): `"user"`, `"assistant"`, or `"system"`
  - **content** (string): Message content

#### Optional Parameters
- **r_type** (string): Prompt engineering style
  - `"bpe"`: Basic Prompt Engineering
  - `"bcot"`: Basic Chain of Thoughts
  - `"hcot"`: High Chain of Thoughts
  - `"react"`: Reasoning + Action
  - `"tot"`: Tree of Thoughts

- **ai_research** (boolean): Enable AI research enhancement
  - Default: `false`

- **research_depth** (string): Research depth level
  - `"basic"`: 1-2 research topics
  - `"medium"`: 3-4 research topics
  - `"high"`: 5-6 research topics
  - Default: `"basic"`

- **temperature** (float): Sampling temperature (0.0-2.0)
  - Default: `0.7`

- **max_tokens** (integer): Maximum tokens in response
- **top_p** (float): Nucleus sampling parameter
- **frequency_penalty** (float): Frequency penalty (-2.0 to 2.0)
- **presence_penalty** (float): Presence penalty (-2.0 to 2.0)
- **stop** (string|array): Stop sequences

### Response

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Enhanced response with research and prompt engineering..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 300,
    "total_tokens": 450
  }
}
```

## Batch Processing API

### Endpoint
```
POST /v1/batch/process
```

### Request Body

```json
{
  "batch": [
    {
      "prompt": "First prompt to process",
      "r_type": "bpe",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    {
      "prompt": "Second prompt to process",
      "r_type": "react",
      "temperature": 0.5
    }
  ],
  "level": "medium",
  "enable_research": true,
  "research_depth": "basic",
  "parallel": true
}
```

### Parameters

#### Required Parameters
- **batch** (array): Array of batch tasks
  - **prompt** (string): The prompt to process
  - **r_type** (string, optional): Prompt engineering style
  - **temperature** (float, optional): Sampling temperature
  - **max_tokens** (integer, optional): Maximum tokens
  - **top_p** (float, optional): Nucleus sampling
  - **frequency_penalty** (float, optional): Frequency penalty
  - **presence_penalty** (float, optional): Presence penalty
  - **stop** (string|array, optional): Stop sequences

- **level** (string): Model level for all tasks

#### Optional Parameters
- **enable_research** (boolean): Enable research for all tasks
  - Default: `false`

- **research_depth** (string): Research depth for all tasks
  - Default: `"basic"`

- **parallel** (boolean): Process tasks in parallel
  - Default: `true`

### Response

```json
{
  "batch_id": "batch_1234567890",
  "total_tasks": 2,
  "successful_tasks": 2,
  "failed_tasks": 0,
  "results": [
    {
      "task_index": 0,
      "success": true,
      "response": {
        "id": "chatcmpl-abc",
        "choices": [...]
      },
      "processing_time_ms": 1500,
      "tokens_used": 150
    },
    {
      "task_index": 1,
      "success": true,
      "response": {
        "id": "chatcmpl-def",
        "choices": [...]
      },
      "processing_time_ms": 2000,
      "tokens_used": 200
    }
  ],
  "total_tokens_used": 350,
  "total_processing_time_ms": 3500,
  "created_at": "2024-01-20T10:30:00Z"
}
```

## User Management API

### User Registration

Create a new user account to get API access.

#### Endpoint
```
POST /v1/users/register
```

#### Request Body
```json
{
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "user_type": "Personal",
  "about_me": "AI enthusiast and developer",
  "hobbies": "Programming, reading, hiking"
}
```

#### Parameters
- **username** (string, required): Username (3-50 characters, alphanumeric with hyphens/underscores)
- **name** (string, required): Full name (2-100 characters)
- **email** (string, required): Valid email address
- **password** (string, required): Password (minimum 8 characters, at least 1 number, 1 uppercase, 1 lowercase)
- **user_type** (string, optional): "Personal" or "Business" (default: "Personal")
- **about_me** (string, optional): User description
- **hobbies** (string, optional): User hobbies

#### Response
```json
{
  "success": true,
  "message": "User registered successfully",
  "user_id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "api_key": "pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y",
  "verification_required": true
}
```

### User Login

Authenticate user and create a session for web applications.

#### Endpoint
```
POST /v1/users/login
```

#### Request Body
```json
{
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

#### Response
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "johndoe",
    "name": "John Doe",
    "email": "john@example.com",
    "user_type": "Personal",
    "subscription_plan": "free",
    "is_verified": false
  },
  "session": {
    "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2024-01-15T12:00:00Z",
    "refresh_expires_at": "2024-02-14T12:00:00Z"
  }
}
```

### Get User Profile

Retrieve current user profile information.

#### Endpoint
```
GET /v1/users/profile
Authorization: Bearer <session_token>
```

#### Response
```json
{
  "id": 1,
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "about_me": "AI enthusiast and developer",
  "hobbies": "Programming, reading, hiking",
  "user_type": "Personal",
  "time_created": "2024-01-01T12:00:00Z",
  "subscription_plan": "free",
  "credits": {
    "main": 5,
    "reset": 5
  },
  "limits": {
    "conversation_limit": 10,
    "reset": 10
  },
  "is_verified": false,
  "last_login": "2024-01-15T12:00:00Z",
  "last_activity": "2024-01-15T12:30:00Z"
}
```

### Update User Profile

Update user profile information.

#### Endpoint
```
PUT /v1/users/profile
Authorization: Bearer <session_token>
```

#### Request Body
```json
{
  "name": "John Smith",
  "about_me": "Updated bio",
  "hobbies": "AI, Machine Learning"
}
```

#### Response
```json
{
  "success": true,
  "message": "Profile updated successfully"
}
```

### Get API Key

Retrieve user's API key (encrypted for security).

#### Endpoint
```
GET /v1/users/api-key
Authorization: Bearer <session_token>
```

#### Response
```json
{
  "success": true,
  "message": "API key retrieved successfully",
  "api_key": "encrypted_api_key_data"
}
```

### Regenerate API Key

Generate a new API key for the user.

#### Endpoint
```
POST /v1/users/api-key/regenerate
Authorization: Bearer <session_token>
```

#### Response
```json
{
  "success": true,
  "message": "API key regenerated successfully",
  "api_key": "encrypted_new_api_key_data"
}
```

### User Logout

Logout user and invalidate session.

#### Endpoint
```
POST /v1/users/logout
Authorization: Bearer <session_token>
```

#### Response
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Admin API

### Health Check

```http
GET /v1/admin/health
Authorization: Bearer sk-78912903
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 12345.67,
  "redis_connected": true,
  "wapi_accessible": true
}
```

### Get System Prompts

```http
GET /v1/admin/system-prompts
Authorization: Bearer sk-78912903
```

Response:
```json
{
  "success": true,
  "message": "System prompts retrieved successfully",
  "data": {
    "prompts": {
      "bpe": "You are an expert AI assistant...",
      "bcot": "You are an expert AI assistant using Basic Chain of Thoughts...",
      ...
    },
    "r_types": ["bpe", "bcot", "hcot", "react", "tot"]
  }
}
```

### Update System Prompt

```http
PUT /v1/admin/system-prompts
Authorization: Bearer sk-78912903
Content-Type: application/json

{
  "r_type": "custom",
  "prompt": "You are a specialized AI assistant for custom tasks..."
}
```

Response:
```json
{
  "success": true,
  "message": "System prompt for 'custom' updated successfully",
  "data": {
    "r_type": "custom"
  }
}
```

### Clear Cache

```http
DELETE /v1/admin/cache
Authorization: Bearer sk-78912903
```

Response:
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

### Get Statistics

```http
GET /v1/admin/stats
Authorization: Bearer sk-78912903
```

Response:
```json
{
  "success": true,
  "message": "Statistics retrieved successfully",
  "data": {
    "cache": {
      "redis_connected": true,
      "memory_cache_size": 42
    },
    "wapi": {
      "accessible": true
    },
    "system": {
      "version": "1.0.0",
      "uptime": 1677652288.123
    }
  }
}
```

## Error Responses

All endpoints return standardized error responses:

```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "details": {
    "request_id": "req_123456",
    "additional_info": "..."
  }
}
```

### Common HTTP Status Codes

- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (invalid API key)
- **429**: Too Many Requests (rate limit exceeded)
- **500**: Internal Server Error

## Rate Limits

### Standard Endpoints
- **Limit**: 100 requests per minute
- **Burst**: 20 requests
- **Headers**: 
  - `X-RateLimit-Limit`: Rate limit
  - `X-RateLimit-Reset`: Reset timestamp
  - `Retry-After`: Seconds to wait

### Batch Endpoints
- **Limit**: 25 requests per minute
- **Burst**: 5 requests

## Best Practices

### Authentication
- Store API keys securely
- Use environment variables for keys
- Rotate keys regularly

### Rate Limiting
- Implement exponential backoff
- Monitor rate limit headers
- Use batch processing for multiple requests

### Caching
- Identical requests are cached automatically
- Research results are cached for 24 hours
- Use cache-friendly request patterns

### Error Handling
- Always check response status codes
- Implement retry logic for 5xx errors
- Log request IDs for debugging

### Performance
- Use appropriate model levels
- Enable research only when needed
- Use batch processing for multiple prompts
- Consider parallel vs sequential processing

## Examples

### Python Client Example

```python
import requests
import json

class PromptEnchancerClient:
    def __init__(self, api_key, base_url="https://api.promptenchanter.net/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, messages, level="medium", r_type=None, 
                       ai_research=False, **kwargs):
        url = f"{self.base_url}/prompt/completions"
        data = {
            "level": level,
            "messages": messages,
            "r_type": r_type,
            "ai_research": ai_research,
            **kwargs
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def batch_process(self, batch, level="medium", enable_research=False, 
                     parallel=True):
        url = f"{self.base_url}/batch/process"
        data = {
            "batch": batch,
            "level": level,
            "enable_research": enable_research,
            "parallel": parallel
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

# Usage
client = PromptEnchancerClient("pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y")

# Simple chat completion
response = client.chat_completion(
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    level="high",
    r_type="hcot",
    ai_research=True
)

print(response["choices"][0]["message"]["content"])

# Batch processing
batch_response = client.batch_process(
    batch=[
        {"prompt": "Explain AI", "r_type": "bpe"},
        {"prompt": "Create a Python function", "r_type": "react"}
    ],
    level="medium",
    enable_research=True
)

for result in batch_response["results"]:
    if result["success"]:
        print(f"Task {result['task_index']}: Success")
    else:
        print(f"Task {result['task_index']}: Failed - {result['error']}")
```

### JavaScript/Node.js Example

```javascript
class PromptEnchancerClient {
    constructor(apiKey, baseUrl = 'https://api.promptenchanter.net/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async chatCompletion(messages, options = {}) {
        const url = `${this.baseUrl}/prompt/completions`;
        const data = {
            level: 'medium',
            messages,
            ...options
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    async batchProcess(batch, options = {}) {
        const url = `${this.baseUrl}/batch/process`;
        const data = {
            batch,
            level: 'medium',
            parallel: true,
            ...options
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }
}

// Usage
const client = new PromptEnchancerClient('pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y');

// Simple chat completion
client.chatCompletion(
    [{ role: 'user', content: 'Explain quantum computing' }],
    { 
        level: 'high', 
        r_type: 'hcot', 
        ai_research: true 
    }
).then(response => {
    console.log(response.choices[0].message.content);
}).catch(error => {
    console.error('Error:', error);
});
```

## User Management Examples

### Python Client with User Management

```python
import requests

class PromptEnchancerUserClient:
    def __init__(self, base_url="https://api.promptenchanter.net/v1"):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self.session_token = None
        self.api_key = None
    
    def register(self, username, name, email, password, user_type="Personal"):
        """Register a new user account"""
        url = f"{self.base_url}/users/register"
        data = {
            "username": username,
            "name": name,
            "email": email,
            "password": password,
            "user_type": user_type
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Store API key for future API calls
        self.api_key = result["api_key"]
        return result
    
    def login(self, email, password):
        """Login and get session token"""
        url = f"{self.base_url}/users/login"
        data = {"email": email, "password": password}
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Store session token
        self.session_token = result["session"]["session_token"]
        return result
    
    def get_profile(self):
        """Get user profile"""
        if not self.session_token:
            raise Exception("Not logged in")
        
        url = f"{self.base_url}/users/profile"
        headers = {**self.headers, "Authorization": f"Bearer {self.session_token}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def chat_completion(self, messages, level="medium", **kwargs):
        """Make API call using stored API key"""
        if not self.api_key:
            raise Exception("No API key available")
        
        url = f"{self.base_url}/prompt/completions"
        headers = {**self.headers, "Authorization": f"Bearer {self.api_key}"}
        data = {
            "level": level,
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

# Example usage
client = PromptEnchancerUserClient()

# Register new user
registration = client.register(
    username="johndoe",
    name="John Doe",
    email="john@example.com",
    password="SecurePass123"
)
print(f"Registered! API Key: {registration['api_key']}")

# Use API immediately after registration
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello, test my new account!"}],
    level="medium",
    r_type="bpe"
)
print(f"API Response: {response['choices'][0]['message']['content']}")

# Or login with existing account
client.login("john@example.com", "SecurePass123")
profile = client.get_profile()
print(f"Welcome back, {profile['name']}!")
```

### Complete Registration and Usage Flow

```bash
# 1. Register new user
curl -X POST "https://api.promptenchanter.net/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "name": "John Doe", 
    "email": "john@example.com",
    "password": "SecurePass123",
    "user_type": "Personal"
  }'

# Response includes your API key:
# {
#   "success": true,
#   "api_key": "pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y",
#   ...
# }

# 2. Use API key for chat completion
curl -X POST "https://api.promptenchanter.net/v1/prompt/completions" \
  -H "Authorization: Bearer pe-rqrFLve5ZM63ZL1XtREaiLrlrNreu20Y" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "medium",
    "messages": [{"role": "user", "content": "Hello world!"}],
    "r_type": "bpe"
  }'

# 3. Login to get session token (for web applications)
curl -X POST "https://api.promptenchanter.net/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123"
  }'

# 4. Get profile using session token
curl "https://api.promptenchanter.net/v1/users/profile" \
  -H "Authorization: Bearer <session_token>"
```

This API guide provides comprehensive information for integrating with PromptEnchanter. For additional support, refer to the interactive API documentation at `/docs` when the service is running.