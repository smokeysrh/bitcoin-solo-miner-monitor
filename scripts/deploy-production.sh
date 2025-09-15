#!/bin/bash

# Bitcoin Solo Miner Monitor - Production Deployment Script
# This script automates the production deployment process

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_METHOD="${1:-docker}"  # docker or manual
DOMAIN="${2:-localhost}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if [ "$DEPLOY_METHOD" = "docker" ]; then
        if ! command -v docker &> /dev/null; then
            error "Docker is not installed. Please install Docker first."
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            error "Docker Compose is not installed. Please install Docker Compose first."
            exit 1
        fi
        
        # Check if user is in docker group
        if ! groups | grep -q docker; then
            error "Current user is not in the docker group. Please add user to docker group and re-login."
            exit 1
        fi
    else
        if ! command -v python3 &> /dev/null; then
            error "Python 3 is not installed. Please install Python 3.11+ first."
            exit 1
        fi
        
        if ! command -v node &> /dev/null; then
            error "Node.js is not installed. Please install Node.js 18+ first."
            exit 1
        fi
        
        if ! command -v npm &> /dev/null; then
            error "npm is not installed. Please install npm first."
            exit 1
        fi
    fi
    
    success "Prerequisites check passed"
}

# Verify production configuration
verify_config() {
    log "Verifying production configuration..."
    
    # Check app_config.py
    if grep -q "DEBUG = True" "$PROJECT_ROOT/config/app_config.py"; then
        error "DEBUG is still set to True in config/app_config.py"
        exit 1
    fi
    
    if grep -q "LOG_LEVEL.*DEBUG" "$PROJECT_ROOT/config/app_config.py"; then
        error "LOG_LEVEL is still set to DEBUG in config/app_config.py"
        exit 1
    fi
    
    # Check for development artifacts
    if find "$PROJECT_ROOT" -name "test_*.py" -not -path "*/tests/*" | grep -q .; then
        warning "Found test files outside tests directory. Please review."
    fi
    
    success "Configuration verification passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p "$PROJECT_ROOT/data"
    mkdir -p "$PROJECT_ROOT/logs"
    
    success "Directories created"
}

# Deploy using Docker
deploy_docker() {
    log "Starting Docker deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Build and start services
    log "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build
    
    log "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    timeout=120
    elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        log "Waiting for services... ($elapsed/$timeout seconds)"
    done
    
    if [ $elapsed -ge $timeout ]; then
        error "Services failed to become healthy within $timeout seconds"
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    fi
    
    success "Docker deployment completed"
}

# Deploy manually
deploy_manual() {
    log "Starting manual deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip3 install -r requirements.txt
    
    # Initialize database
    log "Initializing database..."
    python3 src/tools/init_db.py
    
    # Build frontend
    log "Building frontend..."
    cd src/frontend
    npm ci --production
    npm run build
    cd "$PROJECT_ROOT"
    
    success "Manual deployment completed"
    warning "You need to configure a web server (nginx) to serve the frontend and proxy the API"
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    
    # Wait a moment for services to fully start
    sleep 10
    
    # Check API health
    if curl -f -s http://localhost:8000/api/health > /dev/null; then
        success "API health check passed"
    else
        error "API health check failed"
        return 1
    fi
    
    # Check frontend (only for Docker deployment)
    if [ "$DEPLOY_METHOD" = "docker" ]; then
        if curl -f -s http://localhost:80/ > /dev/null; then
            success "Frontend health check passed"
        else
            error "Frontend health check failed"
            return 1
        fi
    fi
    
    success "All health checks passed"
}

# Display deployment information
show_deployment_info() {
    log "Deployment completed successfully!"
    echo
    echo "=== Deployment Information ==="
    echo "Method: $DEPLOY_METHOD"
    echo "Domain: $DOMAIN"
    echo
    
    if [ "$DEPLOY_METHOD" = "docker" ]; then
        echo "Services:"
        docker-compose -f docker-compose.prod.yml ps
        echo
        echo "Access URLs:"
        echo "  Frontend: http://localhost:80"
        echo "  API: http://localhost:8000"
        echo "  API Health: http://localhost:8000/api/health"
        echo
        echo "Management Commands:"
        echo "  View logs: docker-compose -f docker-compose.prod.yml logs -f"
        echo "  Restart: docker-compose -f docker-compose.prod.yml restart"
        echo "  Stop: docker-compose -f docker-compose.prod.yml down"
    else
        echo "Manual deployment completed."
        echo "Next steps:"
        echo "1. Configure nginx or another web server"
        echo "2. Set up SSL certificate"
        echo "3. Configure systemd service for auto-start"
        echo "4. Set up monitoring and backups"
    fi
    
    echo
    echo "Documentation:"
    echo "  Production Guide: docs/PRODUCTION_DEPLOYMENT.md"
    echo "  Deployment Checklist: docs/DEPLOYMENT_CHECKLIST.md"
    echo "  Environment Templates: docs/PRODUCTION_ENV_TEMPLATE.md"
}

# Cleanup on failure
cleanup() {
    if [ $? -ne 0 ]; then
        error "Deployment failed. Cleaning up..."
        if [ "$DEPLOY_METHOD" = "docker" ]; then
            docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
        fi
    fi
}

# Main deployment function
main() {
    echo "=== Bitcoin Solo Miner Monitor - Production Deployment ==="
    echo
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Validate arguments
    if [ "$DEPLOY_METHOD" != "docker" ] && [ "$DEPLOY_METHOD" != "manual" ]; then
        error "Invalid deployment method. Use 'docker' or 'manual'"
        echo "Usage: $0 [docker|manual] [domain]"
        exit 1
    fi
    
    log "Starting deployment with method: $DEPLOY_METHOD"
    
    # Run deployment steps
    check_root
    check_prerequisites
    verify_config
    create_directories
    
    if [ "$DEPLOY_METHOD" = "docker" ]; then
        deploy_docker
    else
        deploy_manual
    fi
    
    run_health_checks
    show_deployment_info
    
    success "Production deployment completed successfully!"
}

# Run main function
main "$@"