# Production Environment Configuration Template

## Environment Variables Template

Create a `.env.prod` file for production environment variables:

```bash
# Application Configuration
MINER_MONITOR_DEBUG=false
MINER_MONITOR_HOST=0.0.0.0
MINER_MONITOR_PORT=8000
MINER_MONITOR_LOG_LEVEL=WARNING

# Database Configuration
MINER_MONITOR_DB_PATH=/app/data/config.db

# Security Configuration
MINER_MONITOR_SECRET_KEY=your-secure-secret-key-here
MINER_MONITOR_CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Network Configuration
MINER_MONITOR_CONNECTION_TIMEOUT=10
MINER_MONITOR_RETRY_ATTEMPTS=3
MINER_MONITOR_RETRY_DELAY=2

# Monitoring Configuration
MINER_MONITOR_DEFAULT_POLLING_INTERVAL=30
MINER_MONITOR_CHART_RETENTION_DAYS=30
MINER_MONITOR_DEFAULT_REFRESH_INTERVAL=10
```

## Nginx Configuration Template

Create `/etc/nginx/sites-available/miner-monitor`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' ws: wss:;" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Frontend (Static Files)
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 7d;
            add_header Cache-Control "public, max-age=604800";
            proxy_pass http://localhost:80;
        }
    }
    
    # API Endpoints
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API rate limiting
        limit_req zone=api burst=20 nodelay;
    }
    
    # WebSocket Connections
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
    
    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}

# Rate limiting configuration
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

## Systemd Service Template

Create `/etc/systemd/system/miner-monitor.service`:

```ini
[Unit]
Description=Bitcoin Solo Miner Monitor
Documentation=https://github.com/your-repo/miner-monitor
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=miner-monitor
Group=miner-monitor
WorkingDirectory=/opt/miner-monitor
ExecStart=/opt/miner-monitor/venv/bin/python run.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=miner-monitor

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/miner-monitor/data /opt/miner-monitor/logs
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

# Environment
Environment=PYTHONPATH=/opt/miner-monitor
EnvironmentFile=-/opt/miner-monitor/.env.prod

[Install]
WantedBy=multi-user.target
```

## Firewall Configuration Template

### UFW (Ubuntu/Debian)
```bash
#!/bin/bash
# Reset firewall
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH access (adjust port as needed)
sudo ufw allow 22/tcp

# HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# API port (only if not behind reverse proxy)
# sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw --force enable

# Show status
sudo ufw status verbose
```

### iptables (CentOS/RHEL)
```bash
#!/bin/bash
# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH access
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# HTTP and HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save rules
service iptables save
```

## Monitoring Configuration Template

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'miner-monitor'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard Template
```json
{
  "dashboard": {
    "title": "Miner Monitor Dashboard",
    "panels": [
      {
        "title": "Active Miners",
        "type": "stat",
        "targets": [
          {
            "expr": "miner_monitor_active_miners_total"
          }
        ]
      },
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "miner_monitor_api_response_time_seconds"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes"
          }
        ]
      }
    ]
  }
}
```

## Backup Script Template

Create `/opt/miner-monitor/scripts/backup.sh`:

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/opt/backups/miner-monitor"
APP_DIR="/opt/miner-monitor"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cp "$APP_DIR/data/config.db" "$BACKUP_DIR/config_db_$DATE.db"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$APP_DIR" config/

# Backup logs (last 7 days)
find "$APP_DIR/logs" -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

# Clean old backups
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete

# Log backup completion
echo "$(date): Backup completed successfully" >> "$APP_DIR/logs/backup.log"
```

## Log Rotation Template

Create `/etc/logrotate.d/miner-monitor`:

```
/opt/miner-monitor/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 miner-monitor miner-monitor
    postrotate
        systemctl reload miner-monitor
    endscript
}
```

## Health Check Script Template

Create `/opt/miner-monitor/scripts/health-check.sh`:

```bash
#!/bin/bash

# Configuration
API_URL="http://localhost:8000/api/health"
FRONTEND_URL="http://localhost:80/"
LOG_FILE="/opt/miner-monitor/logs/health-check.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG_FILE"
}

# Check API health
api_status=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL")
if [ "$api_status" = "200" ]; then
    log_message "API health check: OK"
else
    log_message "API health check: FAILED (HTTP $api_status)"
    exit 1
fi

# Check frontend
frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$frontend_status" = "200" ]; then
    log_message "Frontend health check: OK"
else
    log_message "Frontend health check: FAILED (HTTP $frontend_status)"
    exit 1
fi

log_message "All health checks passed"
exit 0
```

## Usage Instructions

1. **Copy templates**: Copy the relevant templates to your production server
2. **Customize values**: Replace placeholder values with your actual configuration
3. **Set permissions**: Ensure proper file permissions and ownership
4. **Test configuration**: Validate all configurations before deployment
5. **Enable services**: Enable and start all required services
6. **Verify functionality**: Run health checks to ensure everything is working

## Security Notes

- Replace all placeholder values with secure, production-appropriate values
- Use strong SSL certificates from a trusted CA
- Implement proper firewall rules for your environment
- Regularly update and patch all system components
- Monitor logs for security events
- Implement proper backup and recovery procedures