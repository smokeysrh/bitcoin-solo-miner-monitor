# Production Deployment Checklist

## Quick Reference Checklist for Bitcoin Solo Miner Monitor Deployment

### Pre-Deployment Requirements ✅

#### System Requirements
- [ ] Linux/Windows Server/macOS with adequate resources (2GB+ RAM, 10GB+ storage)
- [ ] Docker and Docker Compose installed (recommended)
- [ ] OR Python 3.11+ and Node.js 18+ (manual deployment)
- [ ] SSL certificate obtained for HTTPS
- [ ] Domain name configured and DNS pointing to server

#### Network Requirements
- [ ] Ports 80, 443, 8000 accessible
- [ ] Firewall configured appropriately
- [ ] Network connectivity to miner devices verified

### Configuration Verification ✅

#### Application Settings
- [ ] `DEBUG = False` in `config/app_config.py`
- [ ] `HOST = "0.0.0.0"` for production binding
- [ ] `LOG_LEVEL = "WARNING"` for production logging
- [ ] No hardcoded development IPs or mock data remaining

#### Security Settings
- [ ] CORS origins updated in `src/backend/api/api_service.py`
- [ ] Debug endpoints secured or disabled
- [ ] No development credentials in codebase
- [ ] Production-appropriate connection timeouts configured

### Deployment Steps ✅

#### Docker Deployment (Recommended)
- [ ] `docker-compose.prod.yml` created with production configuration
- [ ] Images built successfully: `docker-compose -f docker-compose.prod.yml build`
- [ ] Services started: `docker-compose -f docker-compose.prod.yml up -d`
- [ ] Health checks passing for both API and frontend containers

#### Manual Deployment (Alternative)
- [ ] Python dependencies installed: `pip install -r requirements.txt`
- [ ] Database initialized: `python src/tools/init_db.py`
- [ ] Frontend built: `cd src/frontend && npm ci && npm run build`
- [ ] Backend service started: `python run.py`
- [ ] Web server configured to serve frontend and proxy API

### Post-Deployment Verification ✅

#### Functionality Tests
- [ ] Web interface accessible at configured domain
- [ ] API health endpoint responding: `GET /api/health`
- [ ] Database connection working (check logs)
- [ ] WebSocket connections functional
- [ ] Can add and monitor test miner successfully

#### Security Verification
- [ ] HTTPS working with valid SSL certificate
- [ ] HTTP redirects to HTTPS properly
- [ ] CORS policy restricting to production domains only
- [ ] No debug information exposed in error responses
- [ ] Firewall rules active and properly configured

#### Performance Baseline
- [ ] Application startup time acceptable (< 30 seconds)
- [ ] API response times reasonable (< 2 seconds)
- [ ] Memory usage within expected limits
- [ ] No memory leaks detected in initial monitoring

### Production Monitoring Setup ✅

#### Logging and Monitoring
- [ ] Log rotation configured for application logs
- [ ] Health check monitoring active (external monitoring service)
- [ ] Disk space monitoring enabled
- [ ] CPU and memory monitoring configured
- [ ] Alert thresholds set for critical metrics

#### Backup and Recovery
- [ ] Database backup strategy implemented
- [ ] Configuration files backed up
- [ ] Recovery procedures documented and tested
- [ ] Backup restoration tested successfully

### Final Production Checklist ✅

#### Documentation
- [ ] Production configuration documented
- [ ] Monitoring procedures documented
- [ ] Troubleshooting guide accessible to operations team
- [ ] Emergency contact information updated
- [ ] User access credentials distributed securely

#### Operational Readiness
- [ ] Operations team trained on monitoring procedures
- [ ] Escalation procedures defined and communicated
- [ ] Maintenance windows scheduled
- [ ] Performance baseline documented
- [ ] Capacity planning completed

### Quick Commands Reference

#### Docker Operations
```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop services
docker-compose -f docker-compose.prod.yml down
```

#### Health Checks
```bash
# API health
curl -f http://localhost:8000/api/health

# Frontend health
curl -f http://localhost:80/

# Container status
docker-compose -f docker-compose.prod.yml ps
```

#### Log Monitoring
```bash
# Application logs (Docker)
docker-compose -f docker-compose.prod.yml logs -f api

# Application logs (Manual)
tail -f logs/app.log

# System logs
journalctl -u miner-monitor -f
```

### Emergency Procedures

#### Service Recovery
1. Check service status: `docker-compose ps` or `systemctl status miner-monitor`
2. Review recent logs for errors
3. Restart services if needed
4. Verify functionality with health checks
5. Escalate if issues persist

#### Rollback Procedure
1. Stop current services
2. Restore previous configuration from backup
3. Restart services with previous version
4. Verify functionality
5. Investigate and document issues

### Success Criteria

Deployment is considered successful when:
- [ ] All checklist items completed
- [ ] Application accessible via HTTPS
- [ ] Can successfully add and monitor miners
- [ ] Real-time data updates working
- [ ] No critical errors in logs
- [ ] Performance within acceptable limits
- [ ] Monitoring and alerting active

**Deployment Date**: ___________  
**Deployed By**: ___________  
**Verified By**: ___________  
**Production URL**: ___________