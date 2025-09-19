#!/usr/bin/env python3
"""
macOS Application Bundle Creator

This script creates a proper .app bundle structure for Bitcoin Solo Miner Monitor
with all dependencies included for seamless macOS integration.
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional

class AppBundleCreator:
    """Creates macOS application bundles with proper structure and metadata."""
    
    def __init__(self, app_name: str = "Bitcoin Solo Miner Monitor", version: str = "0.1.0"):
        self.app_name = app_name
        self.version = version
        self.bundle_identifier = "com.bitcoinsolominormonitor.app"
        self.executable_name = "BitcoinSoloMinerMonitor"
        
        # Paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.installer_dir = Path(__file__).parent.parent
        self.bundle_dir = Path(__file__).parent
        
    def create_bundle_structure(self, output_dir: Path) -> Path:
        """
        Create the basic .app bundle directory structure.
        
        Args:
            output_dir: Directory where the .app bundle will be created
            
        Returns:
            Path to the created .app bundle
        """
        app_bundle = output_dir / f"{self.app_name}.app"
        
        # Remove existing bundle if it exists
        if app_bundle.exists():
            shutil.rmtree(app_bundle)
        
        # Create bundle structure
        contents_dir = app_bundle / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        frameworks_dir = contents_dir / "Frameworks"
        
        for directory in [macos_dir, resources_dir, frameworks_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Created bundle structure: {app_bundle}")
        return app_bundle
    
    def copy_application_files(self, app_bundle: Path) -> None:
        """
        Copy all application files to the bundle Resources directory.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        resources_dir = app_bundle / "Contents" / "Resources"
        
        # Copy main application files
        files_to_copy = [
            "run.py",
            "requirements.txt",
            "src/",
            "config/",
            "assets/",
        ]
        
        for item in files_to_copy:
            source_path = self.project_root / item
            if source_path.exists():
                if source_path.is_file():
                    shutil.copy2(source_path, resources_dir)
                    print(f"📄 Copied file: {item}")
                else:
                    dest_path = resources_dir / item
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"📁 Copied directory: {item}")
            else:
                print(f"⚠️  Warning: {item} not found, skipping")
    
    def create_info_plist(self, app_bundle: Path) -> None:
        """
        Create the Info.plist file with proper macOS application metadata.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        info_plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{self.executable_name}</string>
    <key>CFBundleIdentifier</key>
    <string>{self.bundle_identifier}</string>
    <key>CFBundleName</key>
    <string>{self.app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{self.app_name}</string>
    <key>CFBundleVersion</key>
    <string>{self.version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.version}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>BSMM</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
    <key>NSHumanReadableCopyright</key>
    <string>© 2024 Bitcoin Solo Miner Monitor. Open Source Software.</string>
    <key>CFBundleGetInfoString</key>
    <string>{self.app_name} {self.version}, © 2024 Bitcoin Solo Miner Monitor</string>
    <key>CFBundleIconFile</key>
    <string>app_icon.icns</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSExceptionDomains</key>
        <dict>
            <key>localhost</key>
            <dict>
                <key>NSExceptionAllowsInsecureHTTPLoads</key>
                <true/>
            </dict>
        </dict>
    </dict>
    <key>LSMinimumSystemVersionByArchitecture</key>
    <dict>
        <key>x86_64</key>
        <string>10.15</string>
        <key>arm64</key>
        <string>11.0</string>
    </dict>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSUIElement</key>
    <false/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key>
            <string>Bitcoin Solo Miner Monitor Configuration</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>bsmm</string>
            </array>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
        </dict>
    </array>
    <key>UTExportedTypeDeclarations</key>
    <array>
        <dict>
            <key>UTTypeIdentifier</key>
            <string>com.bitcoinsolominormonitor.configuration</string>
            <key>UTTypeDescription</key>
            <string>Bitcoin Solo Miner Monitor Configuration</string>
            <key>UTTypeConformsTo</key>
            <array>
                <string>public.data</string>
            </array>
            <key>UTTypeTagSpecification</key>
            <dict>
                <key>public.filename-extension</key>
                <array>
                    <string>bsmm</string>
                </array>
            </dict>
        </dict>
    </array>
</dict>
</plist>'''
        
        info_plist_path = app_bundle / "Contents" / "Info.plist"
        with open(info_plist_path, 'w') as f:
            f.write(info_plist_content)
        
        print(f"✅ Created Info.plist with proper macOS metadata")
    
    def create_launcher_script(self, app_bundle: Path) -> None:
        """
        Create the main executable launcher script with Python runtime support.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        launcher_content = f'''#!/bin/bash
# Launcher script for {self.app_name} with bundled Python runtime support

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
APP_DIR="${{SCRIPT_DIR}}/../Resources"
FRAMEWORKS_DIR="${{SCRIPT_DIR}}/../Frameworks"
SITE_PACKAGES="${{APP_DIR}}/site-packages"

# Change to the application directory
cd "${{APP_DIR}}"

# Set up Python path to include bundled dependencies
export PYTHONPATH="${{SITE_PACKAGES}}:${{PYTHONPATH}}"

# Function to show error dialog
show_error() {{
    osascript -e "display dialog \\"$1\\" buttons {{\\"OK\\"}} default button \\"OK\\" with icon caution with title \\"{self.app_name}\\""
}}

# Function to show info dialog
show_info() {{
    osascript -e "display dialog \\"$1\\" buttons {{\\"OK\\"}} default button \\"OK\\" with icon note with title \\"{self.app_name}\\" giving up after 3"
}}

# Try to find Python in order of preference
PYTHON_CMD=""

# 1. Try bundled Python first
if [ -x "${{FRAMEWORKS_DIR}}/Python.framework/Current/bin/python3" ]; then
    PYTHON_CMD="${{FRAMEWORKS_DIR}}/Python.framework/Current/bin/python3"
    echo "Using bundled Python runtime"
elif [ -x "${{FRAMEWORKS_DIR}}/Python.framework/python3" ]; then
    PYTHON_CMD="${{FRAMEWORKS_DIR}}/Python.framework/python3"
    echo "Using bundled Python runtime"
# 2. Try system Python 3
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    echo "Using system Python 3"
# 3. Try generic python command (check if it's Python 3)
elif command -v python >/dev/null 2>&1; then
    if python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
        PYTHON_CMD="python"
        echo "Using system Python"
    fi
fi

# Check if we found a suitable Python
if [ -z "$PYTHON_CMD" ]; then
    show_error "Python 3.11 or later is required but not found.\\n\\nPlease install Python from python.org or use Homebrew:\\nbrew install python@3.11"
    exit 1
fi

# Check Python version (require 3.11+)
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{{sys.version_info.major}}.{{sys.version_info.minor}}')" 2>/dev/null)
if [ -z "$PYTHON_VERSION" ]; then
    show_error "Unable to determine Python version. Please ensure Python 3.11+ is properly installed."
    exit 1
fi

# Verify minimum Python version (3.11)
if ! $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    show_error "Python ${{PYTHON_VERSION}} found, but Python 3.11 or later is required.\\n\\nPlease update your Python installation from python.org"
    exit 1
fi

echo "Using Python ${{PYTHON_VERSION}} at ${{PYTHON_CMD}}"

# Install missing dependencies if requirements.txt exists and site-packages is incomplete
if [ -f "requirements.txt" ] && [ ! -f "${{SITE_PACKAGES}}/.dependencies_installed" ]; then
    echo "Installing Python dependencies for first run..."
    
    # Show progress dialog (non-blocking)
    show_info "Installing Python dependencies for first run. This may take a moment..." &
    
    # Create site-packages directory if it doesn't exist
    mkdir -p "${{SITE_PACKAGES}}"
    
    # Install dependencies
    if $PYTHON_CMD -m pip install --target "$SITE_PACKAGES" -r requirements.txt --no-deps --quiet 2>/dev/null; then
        touch "${{SITE_PACKAGES}}/.dependencies_installed"
        echo "✅ Dependencies installed successfully"
    else
        echo "⚠️  Warning: Some dependencies may not have installed correctly"
        echo "Attempting alternative installation method..."
        
        # Try without --no-deps flag as fallback
        if $PYTHON_CMD -m pip install --target "$SITE_PACKAGES" -r requirements.txt --quiet 2>/dev/null; then
            touch "${{SITE_PACKAGES}}/.dependencies_installed"
            echo "✅ Dependencies installed successfully (alternative method)"
        else
            echo "❌ Failed to install dependencies automatically"
            show_error "Failed to install Python dependencies automatically.\\n\\nPlease install manually:\\npip3 install -r requirements.txt"
        fi
    fi
fi

# Set additional environment variables for the application
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Launch the application
echo "🚀 Starting {self.app_name}..."
echo "📁 Working directory: ${{APP_DIR}}"
echo "🐍 Python command: ${{PYTHON_CMD}}"
echo "📦 Python path: ${{PYTHONPATH}}"

# Execute the main application
exec $PYTHON_CMD run.py "$@"
'''
        
        launcher_path = app_bundle / "Contents" / "MacOS" / self.executable_name
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)
        
        print(f"✅ Created launcher script: {self.executable_name}")
    
    def create_app_icon(self, app_bundle: Path) -> None:
        """
        Create or convert application icon to .icns format.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        resources_dir = app_bundle / "Contents" / "Resources"
        icon_source = self.project_root / "assets" / "bitcoin-symbol.png"
        icon_dest = resources_dir / "app_icon.icns"
        
        if not icon_source.exists():
            print(f"⚠️  Warning: Icon source not found: {icon_source}")
            return
        
        # Try to convert PNG to ICNS using sips (macOS built-in tool)
        try:
            subprocess.run([
                "sips", "-s", "format", "icns", 
                str(icon_source), "--out", str(icon_dest)
            ], check=True, capture_output=True)
            print(f"✅ Created app icon: app_icon.icns")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not convert icon to ICNS format: {e}")
            # Fallback: copy PNG as is
            shutil.copy2(icon_source, resources_dir / "app_icon.png")
            print(f"📄 Copied PNG icon as fallback")
        except FileNotFoundError:
            print(f"⚠️  Warning: sips command not found, copying PNG as fallback")
            shutil.copy2(icon_source, resources_dir / "app_icon.png")
    
    def install_python_dependencies(self, app_bundle: Path) -> None:
        """
        Pre-install Python dependencies into the bundle.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        resources_dir = app_bundle / "Contents" / "Resources"
        site_packages_dir = resources_dir / "site-packages"
        requirements_file = resources_dir / "requirements.txt"
        
        if not requirements_file.exists():
            print("⚠️  Warning: requirements.txt not found, skipping dependency installation")
            return
        
        # Create site-packages directory
        site_packages_dir.mkdir(exist_ok=True)
        
        print("📚 Installing Python dependencies into bundle...")
        
        try:
            # Install dependencies to the bundle
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "--target", str(site_packages_dir),
                "--requirement", str(requirements_file),
                "--no-deps",
                "--no-cache-dir",
                "--quiet"
            ], check=True, capture_output=True)
            
            # Create marker file
            marker_file = site_packages_dir / ".dependencies_installed"
            marker_file.touch()
            
            print("✅ Python dependencies installed successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not pre-install all dependencies: {e}")
            print("Dependencies will be installed at runtime instead")
    
    def create_launchpad_integration(self, app_bundle: Path) -> None:
        """
        Ensure proper Launchpad and Applications folder integration.
        
        Args:
            app_bundle: Path to the .app bundle
        """
        # Create a desktop services database refresh script
        refresh_script = app_bundle.parent / "refresh_launchpad.sh"
        
        refresh_content = f'''#!/bin/bash
# Refresh Launchpad and desktop services database for {self.app_name}

echo "🔄 Refreshing Launchpad and desktop services..."

# Kill Dock to refresh Launchpad
killall Dock 2>/dev/null || true

# Refresh desktop services database
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user

# Touch the app bundle to update modification time
touch "{app_bundle}"

echo "✅ Launchpad refresh complete"
echo "The application should now appear in Launchpad and Applications folder"
'''
        
        with open(refresh_script, 'w') as f:
            f.write(refresh_content)
        
        os.chmod(refresh_script, 0o755)
        
        print(f"✅ Created Launchpad integration script")
    
    def validate_bundle(self, app_bundle: Path) -> bool:
        """
        Validate the created app bundle structure and metadata.
        
        Args:
            app_bundle: Path to the .app bundle
            
        Returns:
            True if bundle is valid, False otherwise
        """
        print("🔍 Validating app bundle structure...")
        
        required_files = [
            "Contents/Info.plist",
            f"Contents/MacOS/{self.executable_name}",
            "Contents/Resources/run.py",
            "Contents/Resources/requirements.txt"
        ]
        
        required_dirs = [
            "Contents",
            "Contents/MacOS", 
            "Contents/Resources",
            "Contents/Frameworks"
        ]
        
        # Check required directories
        for dir_path in required_dirs:
            full_path = app_bundle / dir_path
            if not full_path.is_dir():
                print(f"❌ Missing required directory: {dir_path}")
                return False
        
        # Check required files
        for file_path in required_files:
            full_path = app_bundle / file_path
            if not full_path.exists():
                print(f"❌ Missing required file: {file_path}")
                return False
        
        # Check executable permissions
        executable_path = app_bundle / "Contents" / "MacOS" / self.executable_name
        if not os.access(executable_path, os.X_OK):
            print(f"❌ Executable not executable: {executable_path}")
            return False
        
        # Validate Info.plist
        info_plist_path = app_bundle / "Contents" / "Info.plist"
        try:
            # Try to parse the plist (basic validation)
            subprocess.run([
                "plutil", "-lint", str(info_plist_path)
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"❌ Invalid Info.plist format")
            return False
        except FileNotFoundError:
            print(f"⚠️  Warning: plutil not found, skipping plist validation")
        
        print("✅ App bundle validation passed")
        return True
    
    def create_bundle(self, output_dir: Path) -> Path:
        """
        Create a complete macOS application bundle.
        
        Args:
            output_dir: Directory where the .app bundle will be created
            
        Returns:
            Path to the created .app bundle
        """
        print(f"🍎 Creating macOS application bundle for {self.app_name} v{self.version}")
        
        # Create bundle structure
        app_bundle = self.create_bundle_structure(output_dir)
        
        # Copy application files
        self.copy_application_files(app_bundle)
        
        # Create Info.plist with proper metadata
        self.create_info_plist(app_bundle)
        
        # Create launcher script
        self.create_launcher_script(app_bundle)
        
        # Create application icon
        self.create_app_icon(app_bundle)
        
        # Install Python dependencies
        self.install_python_dependencies(app_bundle)
        
        # Create Launchpad integration
        self.create_launchpad_integration(app_bundle)
        
        # Validate the bundle
        if not self.validate_bundle(app_bundle):
            raise RuntimeError("App bundle validation failed")
        
        print(f"✅ macOS application bundle created successfully: {app_bundle}")
        return app_bundle


def main():
    """Main function for creating macOS app bundle."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create macOS application bundle")
    parser.add_argument("--output", "-o", required=True, help="Output directory for .app bundle")
    parser.add_argument("--version", "-v", default="0.1.0", help="Application version")
    parser.add_argument("--name", "-n", default="Bitcoin Solo Miner Monitor", help="Application name")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the bundle
    creator = AppBundleCreator(args.name, args.version)
    app_bundle = creator.create_bundle(output_dir)
    
    print(f"\n🎉 Success! macOS application bundle created:")
    print(f"📁 Location: {app_bundle}")
    print(f"📏 Size: {get_directory_size(app_bundle):.1f} MB")
    print(f"\n📋 Next steps:")
    print(f"1. Test the application: open '{app_bundle}'")
    print(f"2. Move to Applications: mv '{app_bundle}' /Applications/")
    print(f"3. Refresh Launchpad: ./refresh_launchpad.sh")


def get_directory_size(path: Path) -> float:
    """Get directory size in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)


if __name__ == "__main__":
    main()