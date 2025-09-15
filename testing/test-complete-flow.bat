@echo off
REM Bitcoin Solo Miner Monitor - Test Complete User Flow
REM Simple script to test the entire user experience from start to finish

echo ========================================
echo Bitcoin Solo Miner Monitor
echo Complete User Flow Test
echo ========================================
echo.
echo This script will guide you through testing the complete user experience:
echo 1. Install Wizard (simulated installation)
echo 2. Application Setup (first-run configuration)
echo 3. Main Application (monitoring interface)
echo.

:MENU
echo ========================================
echo Choose what you want to test:
echo ========================================
echo.
echo 1. Test Install Wizard Only
echo 2. Test Main Application Only  
echo 3. Test Complete Flow (Install + App)
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto INSTALL_WIZARD
if "%choice%"=="2" goto MAIN_APP
if "%choice%"=="3" goto COMPLETE_FLOW
if "%choice%"=="4" goto EXIT
echo Invalid choice. Please try again.
goto MENU

:INSTALL_WIZARD
echo.
echo ========================================
echo Testing Install Wizard
echo ========================================
echo.
echo This will open the installation wizard where you can:
echo - Choose installation options
echo - Scan for miners on your network
echo - Configure initial settings
echo - Simulate the installation process
echo.
echo Press any key to start the Install Wizard...
pause >nul

REM Install Wizard Code
echo [1/4] Checking if Node.js is installed...
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
    goto MENU
)
echo [SUCCESS] Node.js is installed

echo.
echo [2/4] Navigating to installer directory...
cd /d "%~dp0installer\common\wizard"
if errorlevel 1 (
    echo [ERROR] Could not find installer directory!
    echo Make sure you're running this script from the project root.
    pause
    goto MENU
)
echo [SUCCESS] Found installer directory

echo.
echo [3/4] Installing installer dependencies...
echo This may take a few minutes the first time...
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    cd /d "%~dp0"
    goto MENU
)
echo [SUCCESS] Dependencies installed

echo.
echo [4/4] Launching Install Wizard...
echo.
echo ========================================
echo The Install Wizard will now open!
echo ========================================
echo.
call npm start

cd /d "%~dp0"
goto MENU

:MAIN_APP
echo.
echo ========================================
echo Testing Main Application
echo ========================================
echo.
echo This will start the main application where you can:
echo - Go through the First-Run Setup Wizard
echo - Add and configure miners
echo - View the monitoring dashboard
echo - Test all application features
echo.
echo Press any key to start the Main Application...
pause >nul

REM Main Application Code
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
        goto MENU
    )
)
echo [SUCCESS] Python is installed

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
    goto MENU
)
echo [SUCCESS] Node.js is installed

echo.
echo [3/6] Installing Python dependencies...
echo This may take a few minutes the first time...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies!
    echo Please check your internet connection and try again.
    pause
    goto MENU
)
echo [SUCCESS] Python dependencies installed

echo.
echo [4/6] Installing frontend dependencies...
cd /d "%~dp0src\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies!
    echo Please check your internet connection and try again.
    cd /d "%~dp0"
    goto MENU
)
echo [SUCCESS] Frontend dependencies installed

echo.
echo [5/6] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Failed to build frontend!
    cd /d "%~dp0"
    pause
    goto MENU
)
echo [SUCCESS] Frontend built successfully

cd /d "%~dp0"

echo.
echo [6/6] Initializing database...
python src\tools\init_db.py
if errorlevel 1 (
    echo [ERROR] Failed to initialize database!
    pause
    goto MENU
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

goto MENU

:COMPLETE_FLOW
echo.
echo ========================================
echo Testing Complete User Flow
echo ========================================
echo.
echo This will test the complete user experience:
echo.
echo STEP 1: Install Wizard
echo - Simulates what a new user sees when installing
echo - Configure installation preferences
echo - Scan for miners during installation
echo.
echo STEP 2: Main Application  
echo - First-run setup wizard
echo - Configure discovered miners
echo - Access the monitoring dashboard
echo.
echo Ready to start the complete flow test?
echo Press any key to begin with the Install Wizard...
pause >nul

REM Step 1: Install Wizard
echo.
echo ========================================
echo STEP 1: Install Wizard
echo ========================================

REM Install Wizard Code
echo [1/4] Checking if Node.js is installed...
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
    goto MENU
)
echo [SUCCESS] Node.js is installed

echo.
echo [2/4] Navigating to installer directory...
cd /d "%~dp0installer\common\wizard"
if errorlevel 1 (
    echo [ERROR] Could not find installer directory!
    echo Make sure you're running this script from the project root.
    pause
    goto MENU
)
echo [SUCCESS] Found installer directory

echo.
echo [3/4] Installing installer dependencies...
echo This may take a few minutes the first time...
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    cd /d "%~dp0"
    goto MENU
)
echo [SUCCESS] Dependencies installed

echo.
echo [4/4] Launching Install Wizard...
echo.
echo ========================================
echo The Install Wizard will now open!
echo ========================================
echo.
call npm start

cd /d "%~dp0"

echo.
echo ========================================
echo Install Wizard Complete!
echo ========================================
echo.
echo Now we'll start the main application to complete the flow.
echo This simulates what happens after installation when the user
echo first launches the application.
echo.
echo Press any key to continue to the Main Application...
pause >nul

REM Step 2: Main Application
echo.
echo ========================================
echo STEP 2: Main Application
echo ========================================

REM Main Application Code
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
        goto MENU
    )
)
echo [SUCCESS] Python is installed

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
    goto MENU
)
echo [SUCCESS] Node.js is installed

echo.
echo [3/6] Installing Python dependencies...
echo This may take a few minutes the first time...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies!
    echo Please check your internet connection and try again.
    pause
    goto MENU
)
echo [SUCCESS] Python dependencies installed

echo.
echo [4/6] Installing frontend dependencies...
cd /d "%~dp0src\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies!
    echo Please check your internet connection and try again.
    cd /d "%~dp0"
    goto MENU
)
echo [SUCCESS] Frontend dependencies installed

echo.
echo [5/6] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Failed to build frontend!
    cd /d "%~dp0"
    pause
    goto MENU
)
echo [SUCCESS] Frontend built successfully

cd /d "%~dp0"

echo.
echo [6/6] Initializing database...
python src\tools\init_db.py
if errorlevel 1 (
    echo [ERROR] Failed to initialize database!
    pause
    goto MENU
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

goto MENU

:EXIT
echo.
echo ========================================
echo Test Complete
echo ========================================
echo.
echo Thank you for testing Bitcoin Solo Miner Monitor!
echo.
echo If you found any issues, please note:
echo - What step you were on
echo - What you expected to happen
echo - What actually happened
echo - Any error messages you saw
echo.
pause
exit /b 0