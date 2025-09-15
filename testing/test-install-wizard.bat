@echo off
REM Bitcoin Solo Miner Monitor - Test Install Wizard
REM Simple script to test the complete installation experience

echo ========================================
echo Bitcoin Solo Miner Monitor
echo Install Wizard Test Script
echo ========================================
echo.

REM Check if Node.js is installed
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
    exit /b 1
)
echo [SUCCESS] Node.js is installed

REM Navigate to installer directory
echo.
echo [2/4] Navigating to installer directory...
cd /d "%~dp0installer\common\wizard"
if errorlevel 1 (
    echo [ERROR] Could not find installer directory!
    echo Make sure you're running this script from the project root.
    pause
    exit /b 1
)
echo [SUCCESS] Found installer directory

REM Install dependencies
echo.
echo [3/4] Installing installer dependencies...
echo This may take a few minutes the first time...
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed

REM Launch the installer wizard
echo.
echo [4/4] Launching Install Wizard...
echo.
echo ========================================
echo The Install Wizard will now open!
echo ========================================
echo.
echo What you'll see:
echo - A desktop application window will open
echo - Follow the wizard steps to test installation
echo - This is a SAFE TEST - nothing will be installed to your system
echo - You can close the wizard window anytime
echo.
echo Press any key to launch the wizard...
pause >nul

call npm start

echo.
echo ========================================
echo Install Wizard Test Complete
echo ========================================
echo.
echo If you encountered any issues, please check:
echo 1. Node.js is properly installed
echo 2. You have internet connection
echo 3. You're running this from the project root directory
echo.
pause