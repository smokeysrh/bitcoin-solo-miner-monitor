@echo off
REM Icon Creation Script for Bitcoin Solo Miner Monitor
REM This script creates placeholder icons from the existing Bitcoin symbol

echo === Creating Installer Icons ===

set "ASSETS_DIR=%~dp0"
set "PROJECT_ASSETS=%~dp0..\..\assets"

REM Check if ImageMagick is available for icon conversion
where magick >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] ImageMagick found, creating high-quality icons...
    
    REM Create installer icon
    magick "%PROJECT_ASSETS%\bitcoin-symbol.png" -resize 48x48 "%ASSETS_DIR%\installer_icon.ico"
    
    REM Create application icon
    magick "%PROJECT_ASSETS%\bitcoin-symbol.png" -resize 32x32 "%ASSETS_DIR%\app_icon.ico"
    
    REM Create uninstaller icon
    magick "%PROJECT_ASSETS%\bitcoin-symbol.png" -resize 32x32 -modulate 50,100,100 "%ASSETS_DIR%\uninstaller_icon.ico"
    
    echo [SUCCESS] High-quality icons created with ImageMagick
) else (
    echo [INFO] ImageMagick not found, copying PNG files as placeholders...
    
    REM Copy PNG files as placeholders (NSIS can handle PNG in some cases)
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\installer_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\app_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\uninstaller_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\web_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\console_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\doc_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\folder_icon.ico"
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\python_icon.ico"
    
    echo [INFO] Placeholder icons created from PNG files
)

REM Create bitmap images for installer UI
echo [INFO] Creating installer UI bitmaps...

REM Create welcome image (164x314 pixels recommended)
if exist "%PROJECT_ASSETS%\bitcoin-symbol.png" (
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\welcome_image.bmp"
    echo [INFO] Welcome image created
)

REM Create header image (150x57 pixels recommended)
if exist "%PROJECT_ASSETS%\bitcoin-symbol.png" (
    copy "%PROJECT_ASSETS%\bitcoin-symbol.png" "%ASSETS_DIR%\header_image.bmp"
    echo [INFO] Header image created
)

echo.
echo [SUCCESS] Installer assets created successfully!
echo.
echo Created files:
dir "%ASSETS_DIR%\*.ico" /b
dir "%ASSETS_DIR%\*.bmp" /b
echo.
echo Note: For production use, consider creating proper ICO and BMP files
echo with appropriate dimensions and color depths.

pause