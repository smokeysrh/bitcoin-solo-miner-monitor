@echo off
REM Python Runtime Preparation Script for Windows Installer
REM This script prepares the Python runtime for bundling with the installer

echo === Python Runtime Preparation ===
echo.

set "PROJECT_ROOT=%~dp0..\.."
set "INSTALLER_DIR=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\windows"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11 or later
    pause
    exit /b 1
)

echo [INFO] Python found, proceeding with runtime preparation...

REM Create build directory if it doesn't exist
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

REM Run the Python runtime preparation script
echo [INFO] Preparing Python runtime...
python "%~dp0prepare_python_runtime.py" "%BUILD_DIR%" "%REQUIREMENTS_FILE%"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to prepare Python runtime
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Python runtime prepared successfully!
echo Runtime location: %BUILD_DIR%\python
echo Launcher scripts: %BUILD_DIR%
echo.

REM Test the prepared runtime
echo [INFO] Testing prepared runtime...
cd "%BUILD_DIR%"
call launch.bat --version

if %ERRORLEVEL% neq 0 (
    echo [WARNING] Runtime test failed, but continuing...
) else (
    echo [INFO] Runtime test successful
)

echo.
echo === Runtime Preparation Complete ===

pause