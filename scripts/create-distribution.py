#!/usr/bin/env python3
"""
Bitcoin Solo Miner Monitor - Distribution Builder
Creates platform-specific installers for Windows, macOS, and Linux
"""

import os
import sys
import shutil
import subprocess
import argparse
import json
from pathlib import Path
import tempfile
import zipfile

class DistributionBuilder:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).parent.parent).resolve()
        self.dist_dir = self.project_root / "distribution"
        self.installer_dir = self.project_root / "installer"
        
    def clean_dist_dir(self, platform):
        """Clean the distribution directory for the specified platform"""
        platform_dist = self.dist_dir / platform
        if platform_dist.exists():
            shutil.rmtree(platform_dist)
        platform_dist.mkdir(parents=True, exist_ok=True)
        return platform_dist
        
    def build_frontend(self):
        """Build the Vue.js frontend"""
        frontend_dir = self.project_root / "src" / "frontend"
        if not frontend_dir.exists():
            print("⚠️  Frontend directory not found, skipping frontend build")
            return
            
        print("📦 Building frontend...")
        try:
            # Check if npm is available
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
            
            # Install dependencies first
            subprocess.run(["npm", "ci"], cwd=frontend_dir, check=True)
            
            # Build the frontend
            subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
            print("✅ Frontend build completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Frontend build failed: {e}")
            print("⚠️  Continuing without frontend build...")
        except FileNotFoundError:
            print("⚠️  npm not found, skipping frontend build")
            
    def prepare_app_bundle(self, temp_dir):
        """Prepare the application bundle in a temporary directory"""
        app_dir = temp_dir / "app"
        app_dir.mkdir(exist_ok=True)
        
        print("📁 Preparing application bundle...")
        
        # Copy Python backend
        src_dir = self.project_root / "src"
        if src_dir.exists():
            shutil.copytree(src_dir, app_dir / "src", dirs_exist_ok=True)
            
        # Copy configuration
        config_dir = self.project_root / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, app_dir / "config", dirs_exist_ok=True)
            
        # Copy essential files
        essential_files = ["requirements.txt", "run.py", "README.md"]
        for file in essential_files:
            src_file = self.project_root / file
            if src_file.exists():
                shutil.copy2(src_file, app_dir / file)
                
        # Copy assets if they exist
        assets_dir = self.project_root / "assets"
        if assets_dir.exists():
            shutil.copytree(assets_dir, app_dir / "assets", dirs_exist_ok=True)
            
        return app_dir
        
    def build_windows(self, version):
        """Build Windows NSIS installer"""
        print("🪟 Building Windows installer...")
        
        platform_dist = self.clean_dist_dir("windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_dir = self.prepare_app_bundle(temp_path)
            
            # Check if NSIS installer script exists
            nsis_script = self.installer_dir / "windows" / "installer.nsi"
            if not nsis_script.exists():
                print(f"❌ NSIS script not found: {nsis_script}")
                sys.exit(1)
                
            # Create installer using NSIS
            installer_name = f"BitcoinSoloMinerMonitor-{version}-Setup.exe"
            installer_path = platform_dist / installer_name
            
            try:
                # Run NSIS compiler
                nsis_cmd = [
                    "makensis",
                    f"/DVERSION={version}",
                    f"/DAPP_DIR={app_dir}",
                    f"/DOUTPUT_FILE={installer_path}",
                    str(nsis_script)
                ]
                
                subprocess.run(nsis_cmd, check=True, cwd=self.installer_dir / "windows")
                print(f"✅ Windows installer created: {installer_name}")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ NSIS compilation failed: {e}")
                # Fallback: create a ZIP package
                print("📦 Creating ZIP fallback package...")
                zip_path = platform_dist / f"BitcoinSoloMinerMonitor-{version}-Windows.zip"
                self.create_zip_package(app_dir, zip_path)
                
    def build_macos(self, version):
        """Build macOS DMG installer"""
        print("🍎 Building macOS installer...")
        
        platform_dist = self.clean_dist_dir("macos")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_dir = self.prepare_app_bundle(temp_path)
            
            # Check if DMG creation script exists
            dmg_script = self.installer_dir / "macos" / "create_dmg.sh"
            if not dmg_script.exists():
                print(f"❌ DMG script not found: {dmg_script}")
                # Fallback: create a ZIP package
                print("📦 Creating ZIP fallback package...")
                zip_path = platform_dist / f"BitcoinSoloMinerMonitor-{version}-macOS.zip"
                self.create_zip_package(app_dir, zip_path)
                return
                
            # Create DMG
            dmg_name = f"BitcoinSoloMinerMonitor-{version}.dmg"
            dmg_path = platform_dist / dmg_name
            
            try:
                subprocess.run([
                    "bash", str(dmg_script),
                    str(app_dir),
                    str(dmg_path),
                    version
                ], check=True, cwd=self.installer_dir / "macos")
                
                print(f"✅ macOS DMG created: {dmg_name}")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ DMG creation failed: {e}")
                # Fallback: create a ZIP package
                print("📦 Creating ZIP fallback package...")
                zip_path = platform_dist / f"BitcoinSoloMinerMonitor-{version}-macOS.zip"
                self.create_zip_package(app_dir, zip_path)
                
    def build_linux(self, version):
        """Build Linux packages (DEB, RPM, AppImage)"""
        print("🐧 Building Linux packages...")
        
        platform_dist = self.clean_dist_dir("linux")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_dir = self.prepare_app_bundle(temp_path)
            
            # Build DEB package
            self.build_deb_package(app_dir, platform_dist, version)
            
            # Build RPM package
            self.build_rpm_package(app_dir, platform_dist, version)
            
            # Build AppImage
            self.build_appimage(app_dir, platform_dist, version)
            
    def build_deb_package(self, app_dir, dist_dir, version):
        """Build Debian package"""
        try:
            deb_script = self.installer_dir / "linux" / "build_deb.sh"
            if deb_script.exists():
                subprocess.run([
                    "bash", str(deb_script),
                    str(app_dir),
                    str(dist_dir),
                    version
                ], check=True)
                print("✅ DEB package created")
            else:
                print("⚠️  DEB build script not found, skipping")
        except subprocess.CalledProcessError as e:
            print(f"❌ DEB package creation failed: {e}")
            
    def build_rpm_package(self, app_dir, dist_dir, version):
        """Build RPM package"""
        try:
            rpm_script = self.installer_dir / "linux" / "build_rpm.sh"
            if rpm_script.exists():
                subprocess.run([
                    "bash", str(rpm_script),
                    str(app_dir),
                    str(dist_dir),
                    version
                ], check=True)
                print("✅ RPM package created")
            else:
                print("⚠️  RPM build script not found, skipping")
        except subprocess.CalledProcessError as e:
            print(f"❌ RPM package creation failed: {e}")
            
    def build_appimage(self, app_dir, dist_dir, version):
        """Build AppImage package"""
        try:
            appimage_script = self.installer_dir / "linux" / "build_appimage.sh"
            if appimage_script.exists():
                subprocess.run([
                    "bash", str(appimage_script),
                    str(app_dir),
                    str(dist_dir),
                    version
                ], check=True)
                print("✅ AppImage created")
            else:
                print("⚠️  AppImage build script not found, skipping")
        except subprocess.CalledProcessError as e:
            print(f"❌ AppImage creation failed: {e}")
            
    def create_zip_package(self, app_dir, zip_path):
        """Create a ZIP package as fallback"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(app_dir)
                    zipf.write(file_path, arc_path)
        print(f"✅ ZIP package created: {zip_path.name}")
        
    def build_all_platforms(self, version):
        """Build installers for all platforms"""
        print(f"🚀 Building installers for version {version}")
        
        # Build frontend first
        self.build_frontend()
        
        # Determine current platform and build accordingly
        import platform as plt
        current_platform = plt.system().lower()
        
        if current_platform == "windows":
            self.build_windows(version)
        elif current_platform == "darwin":
            self.build_macos(version)
        elif current_platform == "linux":
            self.build_linux(version)
        else:
            print(f"❌ Unsupported platform: {current_platform}")
            print("Creating fallback ZIP package...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                app_dir = self.prepare_app_bundle(temp_path)
                zip_path = self.dist_dir / f"BitcoinSoloMinerMonitor-{version}-{current_platform}.zip"
                self.create_zip_package(app_dir, zip_path)
            
        print(f"✅ Build completed for {current_platform}")

def main():
    parser = argparse.ArgumentParser(description="Build Bitcoin Solo Miner Monitor installers")
    parser.add_argument("--platform", choices=["windows", "macos", "linux", "all"], 
                       default="all", help="Platform to build for")
    parser.add_argument("--version", required=True, help="Version string (e.g., 1.0.0)")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    builder = DistributionBuilder(args.project_root)
    
    if args.platform == "all":
        builder.build_all_platforms(args.version)
    elif args.platform == "windows":
        builder.build_frontend()
        builder.build_windows(args.version)
    elif args.platform == "macos":
        builder.build_frontend()
        builder.build_macos(args.version)
    elif args.platform == "linux":
        builder.build_frontend()
        builder.build_linux(args.version)

if __name__ == "__main__":
    main()