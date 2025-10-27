@echo off
REM Simple Installer Build Script for v0.9.1
REM No PowerShell, no quote issues, just works

echo ========================================
echo Bitcoin Solo Miner Monitor v0.9.1
echo Simple Installer Builder
echo ========================================
echo.

REM Step 1: Clean and prepare build directory
echo [1/4] Preparing build directory...
if exist "build\windows" rmdir /s /q "build\windows"
mkdir "build\windows"
echo Done.
echo.

REM Step 2: Copy distribution files to build directory
echo [2/4] Copying application files...
xcopy "distribution\BitcoinSoloMinerMonitor\*" "build\windows\" /E /I /Y /Q
if errorlevel 1 (
    echo ERROR: Failed to copy files
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 3: Build installer with NSIS
echo [3/4] Building installer with NSIS...
cd installer\windows
makensis /DVERSION=0.9.1 /DAPP_DIR=..\..\build\windows installer.nsi
if errorlevel 1 (
    echo ERROR: NSIS build failed
    cd ..\..
    pause
    exit /b 1
)
cd ..\..
echo Done.
echo.

REM Step 4: Move installer to distribution folder
echo [4/4] Moving installer to distribution folder...
if exist "installer\windows\BitcoinSoloMinerMonitor-0.9.1-Setup.exe" (
    move /Y "installer\windows\BitcoinSoloMinerMonitor-0.9.1-Setup.exe" "distribution\"
    echo Done.
) else (
    echo ERROR: Installer not found in installer\windows
    pause
    exit /b 1
)
echo.

REM Step 5: Verify final location
echo [5/5] Verifying installer...
if exist "distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe" (
    echo.
    echo ========================================
    echo SUCCESS! Installer created!
    echo ========================================
    echo.
    echo Location: distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe
    dir "distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe" | find "BitcoinSoloMinerMonitor"
    echo.
    echo Ready to upload to GitHub!
    echo.
) else (
    echo ERROR: Installer not found
    pause
    exit /b 1
)

pause
