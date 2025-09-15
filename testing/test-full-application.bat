@echo off
REM Bitcoin Solo Miner Monitor - Test Full Application
REM Simple script to test the complete application experience

echo ========================================
echo Bitcoin Solo Miner Monitor
echo Full Application Test Script
echo ========================================
echo.

REM Check if Python is installed
echo [1/6] Checking if Python is installed...
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed!
        echo.
        echo Please install Python first:
        echo 1. Go to https://python.org
        echo 2. Download and install Python 3.11 or newer
        echo 3. Make sure to check "Add Python to PATH" during installation
        echo 4. Restart your computer
        echo 5. Run this script again
        echo.
        pause
        exit /b 1
    )
)
echo [SUCCESS] Python is installed

REM Check if Node.js is installed
echo.
echo [2/6] Checking if Node.js is installed...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    echo.
    echo Please install Node.js first:
    echo 1. Go to https://nodejs.org
    echo 2. Download and install the LTS version
    echo 3. Restart your computer
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)
echo [SUCCESS] Node.js is installed

REM Install Python dependencies
echo.
echo [3/6] Installing Python dependencies...
echo This may take a few minutes the first time...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo [SUCCESS] Python dependencies installed

REM Install frontend dependencies
echo.
echo [4/6] Installing frontend dependencies...
cd /d "%~dp0src\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo [SUCCESS] Frontend dependencies installed

REM Build frontend
echo.
echo [5/6] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Failed to build frontend!
    pause
    exit /b 1
)
echo [SUCCESS] Frontend built successfully

REM Go back to project root
cd /d "%~dp0"

REM Initialize database
echo.
echo [6/6] Initializing database...
python src\tools\init_db.py
if errorlevel 1 (
    echo [ERROR] Failed to initialize database!
    pause
    exit /b 1
)
echo [SUCCESS] Database initialized

echo.
echo ========================================
echo Starting Bitcoin Solo Miner Monitor
echo ========================================
echo.
echo The application will now start!
echo.
echo What you'll see:
echo - The backend server will start (you'll see log messages)
echo - Open your web browser and go to: http://localhost:8000
echo - You'll see the First-Run Setup Wizard
echo - Follow the wizard to configure your miners
echo.
echo Press Ctrl+C to stop the application when you're done testing.
echo.
echo Press any key to start the application...
pause >nul

echo.
echo Starting application...
echo Open your browser to: http://localhost:8000
echo.
python run.py