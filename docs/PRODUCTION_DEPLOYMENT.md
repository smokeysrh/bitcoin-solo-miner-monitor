# Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Bitcoin Solo Miner Monitoring App in a production environment. The application has been cleaned of all development artifacts and configured for production use.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), Windows Server 2019+, or macOS 10.15+
- **Python**: 3.11 or higher
- **Node.js**: 18.0.0 or higher (for frontend builds)
- **Memory**: Minimum 2GB RAM, 4GB+ recommended
- **Storage**: Minimum 10GB free space
- **Network**: Stable internet connection for miner communication

### Required Software

- Docker and Docker Compose (recommended deployment method)
- OR Python 3.11+ with pip (for manual deployment)
- Reverse proxy (nginx recommended for production)
- SSL certificate for HTTPS (Let's Encrypt recommended)

## Production Configuration

### Application Configuration

The application is pre-configured for production with the following settings in `config/app_config.py`:

```python
DEBUG = False                    # Production mode enabled
HOST = "0.0.0.0"                # Binds to all interfaces
PORT = 8000                     # Default API port
LOG_LEVEL = "WARNING"           # Production logging level
CONNECTION_TIMEOUT = 10         # Real network timeout
RETRY_ATTEMPTS = 3              # Connection retry attempts
```

### Security Configuration

- CORS is configured to restrict origins (update in `src/backend/api/api_service.py`)
- Debug endpoints are secured or disabled
- Verbose logging is reduced to WARNING level
- No hardcoded development credentials remain

## Deployment Methods

### Method 1: Docker Deployment (Recommended)

#### Step 1: Create Docker Compose Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    container_name: miner-monitor-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    container_name: miner-monitor-frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - api
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  default:
    name: miner-monitor-network
```

#### Step 2: Deploy with Docker Compose

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Method 2: Manual Deployment

#### Step 1: Backend Deployment

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Initialize database
python src/tools/init_db.py

# Start the backend service
python run.py
```

#### Step 2: Frontend Deployment

```bash
# Navigate to frontend directory
cd src/frontend

# Install dependencies
npm ci --production

# Build for production
npm run build

# Serve with nginx or another web server
# Copy dist/ contents to web server root
```

## Production Checklist

### Pre-Deployment Checklist

- [ ] **Environment Setup**
  - [ ] Production server provisioned with adequate resources
  - [ ] Required software installed (Docker/Python/Node.js)
  - [ ] Network ports 80, 443, and 8000 accessible
  - [ ] SSL certificate obtained and configured

- [ ] **Security Configuration**
  - [ ] CORS origins updated to production domains
  - [ ] Debug endpoints disabled or secured
  - [ ] Production logging levels configured
  - [ ] No development credentials in codebase

- [ ] **Application Configuration**
  - [ ] `DEBUG = False` in config/app_config.py
  - [ ] `HOST = "0.0.0.0"` for container deployment
  - [ ] `LOG_LEVEL = "WARNING"` for production
  - [ ] Database paths configured correctly

### Deployment Checklist

- [ ] **Build and Deploy**
  - [ ] Application built successfully (Docker images or manual build)
  - [ ] Services started and running
  - [ ] Health checks passing
  - [ ] Logs showing no critical errors

- [ ] **Functionality Verification**
  - [ ] Web interface accessible
  - [ ] API endpoints responding correctly
  - [ ] Database initialization successful
  - [ ] WebSocket connections working

- [ ] **Production Testing**
  - [ ] Add test miner and verify data collection
  - [ ] Test all major UI features
  - [ ] Verify real-time updates working
  - [ ] Test error handling with invalid miner data

### Post-Deployment Checklist

- [ ] **Monitoring Setup**
  - [ ] Log monitoring configured
  - [ ] Health check monitoring active
  - [ ] Disk space monitoring enabled
  - [ ] Performance monitoring baseline established

- [ ] **Backup Configuration**
  - [ ] Database backup strategy implemented
  - [ ] Configuration backup scheduled
  - [ ] Recovery procedures documented

- [ ] **Documentation**
  - [ ] Production configuration documented
  - [ ] Monitoring procedures documented
  - [ ] Troubleshooting guide created
  - [ ] Contact information for support updated

## Manual Configuration Steps

### 1. SSL Certificate Configuration

For HTTPS deployment, configure your reverse proxy (nginx example):

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

### 2. CORS Configuration Update

Update `src/backend/api/api_service.py` to restrict CORS origins:

```python
# Replace this line:
# allow_origins=["*"]

# With your production domains:
allow_origins=[
    "https://your-domain.com",
    "https://www.your-domain.com"
]
```

### 3. Firewall Configuration

Configure firewall rules for production:

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if not behind reverse proxy)
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
```

### 4. System Service Configuration

Create systemd service for automatic startup (manual deployment):

```ini
# /etc/systemd/system/miner-monitor.service
[Unit]
Description=Bitcoin Solo Miner Monitor
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable miner-monitor
sudo systemctl start miner-monitor
sudo systemctl status miner-monitor
```

## Environment Variables

For containerized deployments, you can override configuration using environment variables:

```bash
# Docker environment variables
MINER_MONITOR_DEBUG=false
MINER_MONITOR_HOST=0.0.0.0
MINER_MONITOR_PORT=8000
MINER_MONITOR_LOG_LEVEL=WARNING
```

## Monitoring and Maintenance

### Log Monitoring

Monitor application logs for issues:

```bash
# Docker deployment
docker-compose -f docker-compose.prod.yml logs -f api

# Manual deployment
tail -f logs/app.log
```

### Health Checks

The application provides health check endpoints:

- **API Health**: `GET /api/health`
- **Frontend Health**: `GET /` (should return 200)

### Database Maintenance

Regular maintenance tasks:

```bash
# Backup database
cp data/config.db data/config.db.backup.$(date +%Y%m%d)

# Check database integrity
sqlite3 data/config.db "PRAGMA integrity_check;"
```

### Performance Monitoring

Monitor key metrics:

- CPU and memory usage
- Disk space utilization
- Network connectivity to miners
- Response times for API endpoints
- WebSocket connection stability

## Troubleshooting

### Common Issues

1. **Application won't start**
   - Check logs for Python import errors
   - Verify all dependencies installed
   - Ensure database directory is writable

2. **Miners not connecting**
   - Verify network connectivity to miner IPs
   - Check firewall rules on both server and miners
   - Validate miner API endpoints are accessible

3. **Frontend not loading**
   - Check nginx configuration
   - Verify frontend build completed successfully
   - Ensure API proxy configuration is correct

4. **WebSocket connections failing**
   - Check proxy configuration for WebSocket support
   - Verify no firewall blocking WebSocket traffic
   - Check browser console for connection errors

### Support Contacts

- **Technical Issues**: [Your support contact]
- **Infrastructure**: [Your infrastructure team]
- **Emergency**: [Your emergency contact]

## Security Considerations

### Production Security Checklist

- [ ] All debug endpoints disabled or secured
- [ ] CORS configured for specific domains only
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Firewall configured to allow only necessary ports
- [ ] Regular security updates applied
- [ ] Log monitoring for suspicious activity
- [ ] Database access restricted to application only
- [ ] No sensitive data in logs or error messages

### Regular Security Tasks

- Update dependencies monthly
- Review access logs weekly
- Rotate SSL certificates before expiration
- Monitor for security advisories
- Backup and test recovery procedures

## Performance Optimization

### Recommended Optimizations

1. **Database Optimization**
   - Regular VACUUM operations on SQLite
   - Index optimization for frequently queried data
   - Implement data retention policies

2. **Caching Strategy**
   - Enable nginx caching for static assets
   - Implement API response caching where appropriate
   - Use browser caching headers

3. **Resource Management**
   - Monitor memory usage and adjust container limits
   - Implement connection pooling for database access
   - Optimize miner polling intervals based on network conditions

This completes the production deployment documentation. The application is now ready for production use with all development artifacts removed and production configurations in place.