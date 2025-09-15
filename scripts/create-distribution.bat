@echo off
REM Create Distribution Package for Testing
REM This creates a complete, ready-to-run package for your buddy

echo === Creating Distribution Package ===

set "PROJECT_ROOT=%~dp0.."
set "DIST_DIR=%PROJECT_ROOT%\distribution"
set "APP_DIR=%DIST_DIR%\BitcoinSoloMinerMonitor"

echo [INFO] Cleaning distribution directory...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
mkdir "%APP_DIR%"

echo [INFO] Copying application files...

REM Copy Python backend
xcopy "%PROJECT_ROOT%\src" "%APP_DIR%\src" /E /I /Y

REM Copy configuration
xcopy "%PROJECT_ROOT%\config" "%APP_DIR%\config" /E /I /Y

REM Copy requirements and run script
copy "%PROJECT_ROOT%\requirements.txt" "%APP_DIR%\"
copy "%PROJECT_ROOT%\run.py" "%APP_DIR%\"

REM Copy README
copy "%PROJECT_ROOT%\README.md" "%APP_DIR%\"

echo [INFO] Creating startup script...
echo @echo off > "%APP_DIR%\START_APP.bat"
echo echo === Bitcoin Solo Miner Monitor === >> "%APP_DIR%\START_APP.bat"
echo echo. >> "%APP_DIR%\START_APP.bat"
echo echo [INFO] Starting Bitcoin Solo Miner Monitor... >> "%APP_DIR%\START_APP.bat"
echo echo [INFO] The app will be available at: http://localhost:8000 >> "%APP_DIR%\START_APP.bat"
echo echo. >> "%APP_DIR%\START_APP.bat"
echo echo [INFO] Installing Python dependencies... >> "%APP_DIR%\START_APP.bat"
echo pip install -r requirements.txt >> "%APP_DIR%\START_APP.bat"
echo echo. >> "%APP_DIR%\START_APP.bat"
echo echo [INFO] Starting application... >> "%APP_DIR%\START_APP.bat"
echo python run.py >> "%APP_DIR%\START_APP.bat"
echo pause >> "%APP_DIR%\START_APP.bat"

echo [INFO] Creating installation instructions...
echo # Bitcoin Solo Miner Monitor - Quick Start Guide > "%APP_DIR%\QUICK_START.md"
echo. >> "%APP_DIR%\QUICK_START.md"
echo ## Requirements >> "%APP_DIR%\QUICK_START.md"
echo - Python 3.11 or higher >> "%APP_DIR%\QUICK_START.md"
echo - Windows 10 or later >> "%APP_DIR%\QUICK_START.md"
echo. >> "%APP_DIR%\QUICK_START.md"
echo ## Quick Start >> "%APP_DIR%\QUICK_START.md"
echo 1. Double-click `START_APP.bat` >> "%APP_DIR%\QUICK_START.md"
echo 2. Wait for the app to start >> "%APP_DIR%\QUICK_START.md"
echo 3. Open your browser to http://localhost:8000 >> "%APP_DIR%\QUICK_START.md"
echo 4. Follow the first-run setup wizard >> "%APP_DIR%\QUICK_START.md"
echo. >> "%APP_DIR%\QUICK_START.md"
echo ## Testing with Real Miners >> "%APP_DIR%\QUICK_START.md"
echo - Use the Network Discovery feature to find miners >> "%APP_DIR%\QUICK_START.md"
echo - Add miners manually using their IP addresses >> "%APP_DIR%\QUICK_START.md"
echo - Test all monitoring features >> "%APP_DIR%\QUICK_START.md"
echo. >> "%APP_DIR%\QUICK_START.md"
echo ## Support >> "%APP_DIR%\QUICK_START.md"
echo If you encounter any issues, please report them back for fixing. >> "%APP_DIR%\QUICK_START.md"

echo [INFO] Creating version info...
echo 1.0.0-testing > "%APP_DIR%\VERSION"

echo [INFO] Creating ZIP package...
powershell -Command "Compress-Archive -Path '%APP_DIR%' -DestinationPath '%DIST_DIR%\BitcoinSoloMinerMonitor-v1.0.0-TestBuild.zip' -Force"

echo.
echo [SUCCESS] Distribution package created successfully!
echo.
echo Package location: %DIST_DIR%\BitcoinSoloMinerMonitor-v1.0.0-TestBuild.zip
echo Package size: 
dir "%DIST_DIR%\BitcoinSoloMinerMonitor-v1.0.0-TestBuild.zip" | find "BitcoinSoloMinerMonitor"
echo.
echo === Instructions for Your Buddy ===
echo 1. Send him the ZIP file: BitcoinSoloMinerMonitor-v1.0.0-TestBuild.zip
echo 2. He extracts it to any folder
echo 3. He double-clicks START_APP.bat
echo 4. He opens http://localhost:8000 in his browser
echo 5. He follows the first-run setup wizard
echo.
echo This gives him the complete new-user experience!

pause