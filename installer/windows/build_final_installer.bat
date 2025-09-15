@echo off
REM Bitcoin Solo Miner Monitor - Final Windows Installer Build Script
REM This script builds the complete NSIS installer with all enhancements

echo === Bitcoin Solo Miner Monitor - Final Installer Builder ===
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
    echo Make sure to install the following plugins:
    echo - nsProcess
    echo - nsisunz
    echo - AccessControl
    pause
    exit /b 1
)

echo [INFO] NSIS found, checking for required plugins...

REM Check for required NSIS plugins
set "NSIS_PLUGINS=%PROGRAMFILES(x86)%\NSIS\Plugins\x86-unicode"
if not exist "%NSIS_PLUGINS%\nsProcess.dll" (
    echo [WARNING] nsProcess plugin not found
    echo Download from: https://nsis.sourceforge.io/NsProcess_plugin
)

if not exist "%NSIS_PLUGINS%\nsisunz.dll" (
    echo [WARNING] nsisunz plugin not found  
    echo Download from: https://nsis.sourceforge.io/Nsisunz_plug-in
)

if not exist "%NSIS_PLUGINS%\AccessControl.dll" (
    echo [WARNING] AccessControl plugin not found
    echo Download from: https://nsis.sourceforge.io/AccessControl_plug-in
)

echo [INFO] Proceeding with build...

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

REM Verify all assets exist
echo [INFO] Verifying installer assets...
if exist "assets\installer_icon.ico" (
    echo [INFO] installer_icon.ico found
) else (
    echo [WARNING] installer_icon.ico not found, using placeholder
)

if exist "assets\LICENSE.txt" (
    echo [INFO] LICENSE.txt found
) else (
    echo [WARNING] LICENSE.txt not found
)

REM Build the installer
echo [INFO] Building final NSIS installer...
makensis /DBUILD_DATE="%BUILD_DATE%" /DBUILD_COMMIT="%BUILD_COMMIT%" /DBUILD_NUMBER="%BUILD_NUMBER%" installer_final.nsi

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to build installer
    echo Check the NSIS output above for specific errors
    pause
    exit /b 1
)

REM Move installer to distribution directory
echo [INFO] Moving installer to distribution directory...
move "BitcoinSoloMinerMonitor-1.0.0-Setup.exe" "%DIST_DIR%\"

REM Generate checksums
echo [INFO] Generating checksums...
cd "%DIST_DIR%"
certutil -hashfile "BitcoinSoloMinerMonitor-1.0.0-Setup.exe" SHA256 > "BitcoinSoloMinerMonitor-1.0.0-Setup.exe.sha256"

REM Create installation instructions
echo [INFO] Creating installation instructions...
echo Bitcoin Solo Miner Monitor - Installation Instructions > "INSTALLATION_INSTRUCTIONS.txt"
echo ================================================== >> "INSTALLATION_INSTRUCTIONS.txt"
echo. >> "INSTALLATION_INSTRUCTIONS.txt"
echo 1. Download: BitcoinSoloMinerMonitor-1.0.0-Setup.exe >> "INSTALLATION_INSTRUCTIONS.txt"
echo 2. Verify checksum (optional but recommended): >> "INSTALLATION_INSTRUCTIONS.txt"
echo    Compare SHA256 hash with BitcoinSoloMinerMonitor-1.0.0-Setup.exe.sha256 >> "INSTALLATION_INSTRUCTIONS.txt"
echo 3. Right-click the installer and select "Run as administrator" >> "INSTALLATION_INSTRUCTIONS.txt"
echo 4. Follow the installation wizard >> "INSTALLATION_INSTRUCTIONS.txt"
echo 5. Launch from Desktop or Start Menu >> "INSTALLATION_INSTRUCTIONS.txt"
echo 6. Open http://localhost:8000 in your browser >> "INSTALLATION_INSTRUCTIONS.txt"
echo 7. Complete the first-run setup >> "INSTALLATION_INSTRUCTIONS.txt"
echo. >> "INSTALLATION_INSTRUCTIONS.txt"
echo Security Notes: >> "INSTALLATION_INSTRUCTIONS.txt"
echo - Windows may show "Unknown Publisher" warning - this is normal for open-source software >> "INSTALLATION_INSTRUCTIONS.txt"
echo - Antivirus software may flag mining-related software - add exclusions if needed >> "INSTALLATION_INSTRUCTIONS.txt"
echo - The installer includes a complete Python runtime - no additional software needed >> "INSTALLATION_INSTRUCTIONS.txt"
echo. >> "INSTALLATION_INSTRUCTIONS.txt"
echo Support: Visit %WEBSITE% for documentation and support >> "INSTALLATION_INSTRUCTIONS.txt"

REM Display results
echo.
echo [SUCCESS] Final Windows installer built successfully!
echo.
echo === Build Results ===
echo Installer: %DIST_DIR%\BitcoinSoloMinerMonitor-1.0.0-Setup.exe
echo Checksum: %DIST_DIR%\BitcoinSoloMinerMonitor-1.0.0-Setup.exe.sha256
echo Instructions: %DIST_DIR%\INSTALLATION_INSTRUCTIONS.txt
echo.
dir "%DIST_DIR%\BitcoinSoloMinerMonitor-1.0.0-Setup.exe"
echo.
echo === Installation Features ===
echo ✓ Complete Python runtime bundled
echo ✓ All dependencies included
echo ✓ Professional installer UI
echo ✓ Desktop and Start Menu shortcuts
echo ✓ Windows Add/Remove Programs integration
echo ✓ Network discovery configuration
echo ✓ Clean uninstaller
echo ✓ SHA256 checksum for verification
echo.
echo The installer is ready for distribution!

pause