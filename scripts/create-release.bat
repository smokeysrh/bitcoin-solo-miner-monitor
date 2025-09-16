@echo off
REM Bitcoin Solo Miner Monitor - Release Creator (Windows)
REM Creates a complete release with automated GitHub publishing

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Bitcoin Solo Miner Monitor - Release Creator
echo ========================================
echo.

REM Check if version argument is provided
if "%1"=="" (
    echo Usage: create-release.bat ^<version^> [--dry-run] [--skip-build-wait]
    echo.
    echo Examples:
    echo   create-release.bat 1.0.0
    echo   create-release.bat 1.0.1 --dry-run
    echo   create-release.bat 1.2.0 --skip-build-wait
    echo.
    echo Options:
    echo   --dry-run         Perform a dry run without making changes
    echo   --skip-build-wait Skip waiting for GitHub Actions build completion
    echo.
    exit /b 1
)

set VERSION=%1
set ARGS=

REM Process additional arguments
:argloop
shift
if "%1"=="" goto endargs
set ARGS=%ARGS% %1
goto argloop
:endargs

echo Creating release for version %VERSION%...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11 or later and try again
    exit /b 1
)

REM Check if we're in a git repository
git status >nul 2>&1
if errorlevel 1 (
    echo Error: Not in a git repository
    echo Please run this script from the project root directory
    exit /b 1
)

REM Run the Python release creator
echo Running release creation process...
python scripts\release\create-release.py %VERSION% %ARGS%

if errorlevel 1 (
    echo.
    echo Release creation failed!
    exit /b 1
) else (
    echo.
    echo Release creation completed successfully!
    echo.
    echo Next steps:
    echo 1. Monitor the GitHub Actions build
    echo 2. Test the generated installers
    echo 3. Announce the release to the community
)

endlocal