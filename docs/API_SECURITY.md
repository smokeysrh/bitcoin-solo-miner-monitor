# API Security Configuration

This document describes the security measures implemented for the Bitcoin Solo Miner Monitoring API.

## Security Features

### 1. CORS (Cross-Origin Resource Sharing) Protection

The API now uses restrictive CORS settings instead of allowing all origins:

- **Default Allowed Origins:**
  - `http://localhost:3000` (Development frontend)
  - `http://localhost:8000` (Production frontend)
  - `http://127.0.0.1:3000` (Local development)
  - `http://127.0.0.1:8000` (Local production)

- **Additional Origins:** Set via `ALLOWED_ORIGINS` environment variable (comma-separated)
- **Allowed Methods:** Limited to `GET, POST, PUT, DELETE, OPTIONS`
- **Allowed Headers:** Restricted to `Content-Type, Authorization, X-Requested-With`

### 2. Rate Limiting

All API endpoints are protected by rate limiting:

- **Per Minute:** 120 requests per IP address
- **Per Hour:** 2000 requests per IP address
- **Response:** HTTP 429 with retry-after header when limits exceeded

### 3. API Key Authentication

Sensitive endpoints require API key authentication via Bearer token:

#### Protected Endpoints:
- `POST /api/miners` (Add miner)
- `PUT /api/miners/{id}` (Update miner)
- `DELETE /api/miners/{id}` (Remove miner)
- `POST /api/miners/{id}/restart` (Restart miner)
- `PUT /api/settings` (Update settings)
- `POST /api/miners/bulk` (Bulk operations)

#### Development-Only Endpoints:
- `POST /api/reload-miners` (Requires both dev auth and API key)

### 4. Development Endpoint Protection

Development endpoints are automatically disabled in production:

- **Disabled when:** `ENVIRONMENT=production` or `DEBUG=false`
- **Returns:** HTTP 404 when accessed in production

## Configuration

### Environment Variables

```bash
# API Keys (comma-separated for multiple keys)
API_KEYS="your-secure-api-key-1,your-secure-api-key-2"

# Additional CORS origins (comma-separated)
ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"

# Environment setting
ENVIRONMENT="production"  # or "development"

# Debug mode
DEBUG="false"  # Set to "true" for development
```

### API Key Usage

Include the API key in the Authorization header:

```bash
curl -H "Authorization: Bearer your-secure-api-key" \
     -X POST http://localhost:8000/api/miners \
     -H "Content-Type: application/json" \
     -d '{"type": "antminer", "ip_address": "192.168.1.100", "port": 4028}'
```

### Development Setup

For development, if no API keys are configured and `DEBUG=true`, a fallback key is available:

```bash
# Development fallback key (DO NOT use in production)
API_KEY="dev-key-12345"
```

## Security Best Practices

### 1. API Key Management

- **Generate Strong Keys:** Use cryptographically secure random strings (32+ characters)
- **Rotate Regularly:** Change API keys periodically
- **Environment Variables:** Never hardcode keys in source code
- **Separate Keys:** Use different keys for different environments

### 2. Network Security

- **HTTPS Only:** Always use HTTPS in production
- **Firewall Rules:** Restrict API access to trusted networks
- **Reverse Proxy:** Use nginx/Apache for additional security layers

### 3. Monitoring

- **Rate Limit Logs:** Monitor for rate limit violations
- **Authentication Failures:** Track failed authentication attempts
- **Unusual Patterns:** Watch for suspicious API usage

## Endpoint Classification

### Public Endpoints (No Authentication Required)
- `GET /api/miners` (Read-only miner list)
- `GET /api/miners/{id}` (Read-only miner details)
- `GET /api/miners/{id}/metrics` (Read-only metrics)
- `GET /api/miners/{id}/metrics/latest` (Read-only latest metrics)
- `GET /api/discovery/status` (Read-only discovery status)
- `GET /api/settings` (Read-only settings)
- `GET /api/system/info` (Read-only system info)
- `GET /api/system/metrics` (Read-only system metrics)
- `GET /api/system/metrics/history` (Read-only metrics history)
- `GET /api/setup-status` (Read-only setup status)
- `GET /api/validation/stats` (Read-only validation stats)
- `GET /api/health` (Health check)
- `WebSocket /ws` (Real-time updates)

### Authenticated Endpoints (API Key Required)
- `POST /api/miners` (Create miner)
- `PUT /api/miners/{id}` (Update miner)
- `DELETE /api/miners/{id}` (Delete miner)
- `POST /api/miners/{id}/restart` (Restart miner)
- `POST /api/discovery` (Start discovery)
- `PUT /api/settings` (Update settings)
- `POST /api/miners/bulk` (Bulk operations)

### Development-Only Endpoints (Disabled in Production)
- `POST /api/reload-miners` (Reload from database)

## Troubleshooting

### Common Issues

1. **CORS Errors:** Add your domain to `ALLOWED_ORIGINS`
2. **401 Unauthorized:** Check API key configuration
3. **429 Rate Limited:** Reduce request frequency
4. **404 on Dev Endpoints:** Check `ENVIRONMENT` and `DEBUG` settings

### Testing Authentication

```bash
# Test without API key (should fail)
curl -X POST http://localhost:8000/api/miners

# Test with API key (should succeed)
curl -H "Authorization: Bearer your-api-key" \
     -X POST http://localhost:8000/api/miners \
     -H "Content-Type: application/json" \
     -d '{}'
```