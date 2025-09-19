@echo off
REM Bitcoin Solo Miner Monitor - Windows Installer Build Script
REM This script builds the NSIS installer with Python runtime bundling

echo === Bitcoin Solo Miner Monitor - Windows Installer Builder ===
echo.

set "PROJECT_ROOT=%~dp0..\.."
set "INSTALLER_DIR=%~dp0"
set "BUILD_DIR=%PROJECT_ROOT%\build\windows"
set "DIST_DIR=%PROJECT_ROOT%\distribution"

REM Check for NSIS installation
where makensis >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] NSIS is not installed or not in PATH
    echo Please install NSIS from https://nsis.sourceforge.io/
    pause
    exit /b 1
)

echo [INFO] NSIS found, proceeding with build...

REM Clean and create build directories
echo [INFO] Preparing build environment...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%BUILD_DIR%"
mkdir "%DIST_DIR%"

REM Build frontend if needed
echo [INFO] Building frontend...
cd "%PROJECT_ROOT%\src\frontend"
if exist "package.json" (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install frontend dependencies
        pause
        exit /b 1
    )
    
    echo [INFO] Building frontend...
    call npm run build
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to build frontend
        pause
        exit /b 1
    )
) else (
    echo [INFO] No frontend build required
)

REM Return to installer directory
cd "%INSTALLER_DIR%"

REM Copy application files to build directory
echo [INFO] Copying application files...
xcopy "%PROJECT_ROOT%\src" "%BUILD_DIR%\src" /E /I /Y
xcopy "%PROJECT_ROOT%\config" "%BUILD_DIR%\config" /E /I /Y
copy "%PROJECT_ROOT%\run.py" "%BUILD_DIR%\"
copy "%PROJECT_ROOT%\requirements.txt" "%BUILD_DIR%\"
copy "%PROJECT_ROOT%\README.md" "%BUILD_DIR%\"

REM Create version information
echo [INFO] Generating version information...
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "BUILD_DATE=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%"

REM Get git commit if available
git rev-parse --short HEAD >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f %%i in ('git rev-parse --short HEAD') do set "BUILD_COMMIT=%%i"
) else (
    set "BUILD_COMMIT=unknown"
)

REM Set build number (could be from CI/CD)
if not defined BUILD_NUMBER set "BUILD_NUMBER=1"

echo [INFO] Build Information:
echo   Date: %BUILD_DATE%
echo   Commit: %BUILD_COMMIT%
echo   Number: %BUILD_NUMBER%

REM Create assets if they don't exist
echo [INFO] Preparing installer assets...
if not exist "assets\installer_icon.ico" (
    echo [INFO] Creating placeholder installer icon...
    copy "%PROJECT_ROOT%\assets\bitcoin-symbol.png" "assets\installer_icon.ico" >nul 2>&1
)

if not exist "assets\app_icon.ico" (
    echo [INFO] Creating placeholder app icon...
    copy "%PROJECT_ROOT%\assets\bitcoin-symbol.png" "assets\app_icon.ico" >nul 2>&1
)

REM Build the installer
echo [INFO] Building NSIS installer...
makensis /DBUILD_DATE="%BUILD_DATE%" /DBUILD_COMMIT="%BUILD_COMMIT%" /DBUILD_NUMBER="%BUILD_NUMBER%" installer_enhanced.nsi

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to build installer
    pause
    exit /b 1
)

REM Move installer to distribution directory
echo [INFO] Moving installer to distribution directory...
move "BitcoinSoloMinerMonitor-0.1.0-Setup.exe" "%DIST_DIR%\"

REM Generate checksums
echo [INFO] Generating checksums...
cd "%DIST_DIR%"
certutil -hashfile "BitcoinSoloMinerMonitor-0.1.0-Setup.exe" SHA256 > "BitcoinSoloMinerMonitor-0.1.0-Setup.exe.sha256"

REM Display results
echo.
echo [SUCCESS] Windows installer built successfully!
echo.
echo Installer: %DIST_DIR%\BitcoinSoloMinerMonitor-0.1.0-Setup.exe
echo Checksum: %DIST_DIR%\BitcoinSoloMinerMonitor-0.1.0-Setup.exe.sha256
echo.
dir "%DIST_DIR%\BitcoinSoloMinerMonitor-0.1.0-Setup.exe"
echo.
echo === Build Complete ===

pause