@echo off
REM Bitcoin Solo Miner Monitor - Production Deployment Script (Windows)
REM This script automates the production deployment process on Windows

setlocal enabledelayedexpansion

REM Configuration
set "DEPLOY_METHOD=%1"
set "DOMAIN=%2"

if "%DEPLOY_METHOD%"=="" set "DEPLOY_METHOD=docker"
if "%DOMAIN%"=="" set "DOMAIN=localhost"

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo === Bitcoin Solo Miner Monitor - Production Deployment ===
echo.

REM Validate arguments
if not "%DEPLOY_METHOD%"=="docker" if not "%DEPLOY_METHOD%"=="manual" (
    echo [ERROR] Invalid deployment method. Use 'docker' or 'manual'
    echo Usage: %0 [docker^|manual] [domain]
    exit /b 1
)

echo [INFO] Starting deployment with method: %DEPLOY_METHOD%

REM Check prerequisites
echo [INFO] Checking prerequisites...

if "%DEPLOY_METHOD%"=="docker" (
    docker --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker is not installed. Please install Docker Desktop first.
        exit /b 1
    )
    
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
        exit /b 1
    )
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed. Please install Python 3.11+ first.
        exit /b 1
    )
    
    node --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Node.js is not installed. Please install Node.js 18+ first.
        exit /b 1
    )
    
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npm is not installed. Please install npm first.
        exit /b 1
    )
)

echo [SUCCESS] Prerequisites check passed

REM Verify production configuration
echo [INFO] Verifying production configuration...

findstr /C:"DEBUG = True" "%PROJECT_ROOT%\config\app_config.py" >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] DEBUG is still set to True in config\app_config.py
    exit /b 1
)

echo [SUCCESS] Configuration verification passed

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
echo [SUCCESS] Directories created

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Deploy based on method
if "%DEPLOY_METHOD%"=="docker" (
    echo [INFO] Starting Docker deployment...
    
    echo [INFO] Building Docker images...
    docker-compose -f docker-compose.prod.yml build
    if errorlevel 1 (
        echo [ERROR] Failed to build Docker images
        exit /b 1
    )
    
    echo [INFO] Starting services...
    docker-compose -f docker-compose.prod.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start services
        exit /b 1
    )
    
    echo [INFO] Waiting for services to be healthy...
    timeout /t 30 /nobreak >nul
    
    echo [SUCCESS] Docker deployment completed
) else (
    echo [INFO] Starting manual deployment...
    
    echo [INFO] Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies
        exit /b 1
    )
    
    echo [INFO] Initializing database...
    python src\tools\init_db.py
    if errorlevel 1 (
        echo [ERROR] Failed to initialize database
        exit /b 1
    )
    
    echo [INFO] Building frontend...
    cd src\frontend
    call npm ci --production
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        cd /d "%PROJECT_ROOT%"
        exit /b 1
    )
    
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Failed to build frontend
        cd /d "%PROJECT_ROOT%"
        exit /b 1
    )
    
    cd /d "%PROJECT_ROOT%"
    echo [SUCCESS] Manual deployment completed
    echo [WARNING] You need to configure a web server (IIS/nginx) to serve the frontend and proxy the API
)

REM Run health checks
echo [INFO] Running health checks...
timeout /t 10 /nobreak >nul

curl -f -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] API health check failed
    exit /b 1
)
echo [SUCCESS] API health check passed

if "%DEPLOY_METHOD%"=="docker" (
    curl -f -s http://localhost:80/ >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Frontend health check failed
        exit /b 1
    )
    echo [SUCCESS] Frontend health check passed
)

echo [SUCCESS] All health checks passed

REM Display deployment information
echo.
echo === Deployment Information ===
echo Method: %DEPLOY_METHOD%
echo Domain: %DOMAIN%
echo.

if "%DEPLOY_METHOD%"=="docker" (
    echo Services:
    docker-compose -f docker-compose.prod.yml ps
    echo.
    echo Access URLs:
    echo   Frontend: http://localhost:80
    echo   API: http://localhost:8000
    echo   API Health: http://localhost:8000/api/health
    echo.
    echo Management Commands:
    echo   View logs: docker-compose -f docker-compose.prod.yml logs -f
    echo   Restart: docker-compose -f docker-compose.prod.yml restart
    echo   Stop: docker-compose -f docker-compose.prod.yml down
) else (
    echo Manual deployment completed.
    echo Next steps:
    echo 1. Configure IIS or another web server
    echo 2. Set up SSL certificate
    echo 3. Configure Windows service for auto-start
    echo 4. Set up monitoring and backups
)

echo.
echo Documentation:
echo   Production Guide: docs\PRODUCTION_DEPLOYMENT.md
echo   Deployment Checklist: docs\DEPLOYMENT_CHECKLIST.md
echo   Environment Templates: docs\PRODUCTION_ENV_TEMPLATE.md

echo.
echo [SUCCESS] Production deployment completed successfully!

endlocal