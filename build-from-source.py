#!/usr/bin/env python3
"""
Build From Source Tool for Bitcoin Solo Miner Monitor

This script provides a comprehensive way to build Bitcoin Solo Miner Monitor
installers from source code with reproducible build environment setup.

Usage:
    python3 build-from-source.py --version v1.0.0 --platform all
    python3 build-from-source.py --version v1.0.0 --platform windows
    python3 build-from-source.py --version dev --platform linux --dev-mode
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class BuildEnvironment:
    """Manages reproducible build environment"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.repo_url = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git"
        self.required_python = "3.11.7"
        self.required_node = "18.19.0"
        
    def log(self, message: str, color: str = Colors.WHITE, bold: bool = False):
        """Print colored log message"""
        prefix = f"{Colors.BOLD}" if bold else ""
        print(f"{prefix}{color}{message}{Colors.END}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, 
                   capture_output: bool = True, timeout: int = 300,
                   env: Optional[Dict] = None) -> Tuple[bool, str, str]:
        """Run shell command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.work_dir,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)
    
    def check_prerequisites(self) -> bool:
        """Check if all build prerequisites are available"""
        self.log("🔍 Checking build prerequisites...", Colors.CYAN, bold=True)
        
        required_tools = {
            "git": "Git version control",
            "python3": "Python 3.11+",
            "pip": "Python package installer"
        }
        
        missing_tools = []
        
        for tool, description in required_tools.items():
            if shutil.which(tool):
                self.log(f"✅ {tool}: Found", Colors.GREEN)
            else:
                self.log(f"❌ {tool}: Not found ({description})", Colors.RED)
                missing_tools.append(tool)
        
        # Check Python version
        success, stdout, stderr = self.run_command(["python3", "--version"])
        if success:
            version = stdout.strip().split()[-1]
            if version.startswith("3.11"):
                self.log(f"✅ Python version: {version} (compatible)", Colors.GREEN)
            else:
                self.log(f"⚠️  Python version: {version} (recommended: 3.11.x)", Colors.YELLOW)
        
        # Check Node.js (optional for frontend)
        if shutil.which("node"):
            success, stdout, stderr = self.run_command(["node", "--version"])
            if success:
                version = stdout.strip()
                if version.startswith("v18"):
                    self.log(f"✅ Node.js version: {version} (compatible)", Colors.GREEN)
                else:
                    self.log(f"⚠️  Node.js version: {version} (recommended: v18.x)", Colors.YELLOW)
        else:
            self.log("⚠️  Node.js: Not found (frontend build will be skipped)", Colors.YELLOW)
        
        # Check platform-specific tools
        current_platform = platform.system().lower()
        if current_platform == "windows":
            if shutil.which("makensis"):
                self.log("✅ NSIS: Found", Colors.GREEN)
            else:
                self.log("❌ NSIS: Not found (Windows installer build will fail)", Colors.RED)
                missing_tools.append("makensis")
        elif current_platform == "darwin":
            success, stdout, stderr = self.run_command(["xcode-select", "-p"])
            if success:
                self.log("✅ Xcode Command Line Tools: Found", Colors.GREEN)
            else:
                self.log("❌ Xcode Command Line Tools: Not found", Colors.RED)
                missing_tools.append("xcode-select")
        else:  # Linux
            build_tools = ["gcc", "make"]
            for tool in build_tools:
                if shutil.which(tool):
                    self.log(f"✅ {tool}: Found", Colors.GREEN)
                else:
                    self.log(f"❌ {tool}: Not found", Colors.RED)
                    missing_tools.append(tool)
        
        if missing_tools:
            self.log(f"\n❌ Missing required tools: {', '.join(missing_tools)}", Colors.RED, bold=True)
            self.log("Please install missing tools and try again.", Colors.RED)
            return False
        
        self.log("✅ All prerequisites satisfied!", Colors.GREEN, bold=True)
        return True
    
    def setup_reproducible_environment(self) -> Dict[str, str]:
        """Set up environment variables for reproducible builds"""
        self.log("🔧 Setting up reproducible build environment...", Colors.BLUE)
        
        env = os.environ.copy()
        
        # Reproducible build environment variables
        reproducible_env = {
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": "1704067200",  # 2024-01-01 00:00:00 UTC
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            "NODE_ENV": "production"
        }
        
        env.update(reproducible_env)
        
        for key, value in reproducible_env.items():
            self.log(f"  {key}={value}", Colors.CYAN)
        
        return env
    
    def clone_repository(self, version: str) -> Path:
        """Clone repository and checkout specific version"""
        self.log(f"📥 Cloning repository for version {version}...", Colors.BLUE)
        
        repo_dir = self.work_dir / "bitcoin-solo-miner-monitor"
        
        # Remove existing directory if it exists
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        
        # Clone repository
        success, stdout, stderr = self.run_command([
            "git", "clone", self.repo_url, str(repo_dir)
        ])
        
        if not success:
            raise Exception(f"Failed to clone repository: {stderr}")
        
        # Checkout specific version
        if version != "dev":
            self.log(f"🔄 Checking out version {version}...", Colors.BLUE)
            success, stdout, stderr = self.run_command([
                "git", "checkout", version
            ], cwd=repo_dir)
            
            if not success:
                raise Exception(f"Failed to checkout version {version}: {stderr}")
        
        # Verify clean working tree
        success, stdout, stderr = self.run_command([
            "git", "status", "--porcelain"
        ], cwd=repo_dir)
        
        if success and stdout.strip():
            self.log("⚠️  Working tree is not clean", Colors.YELLOW)
        else:
            self.log("✅ Working tree is clean", Colors.GREEN)
        
        # Get commit information
        success, stdout, stderr = self.run_command([
            "git", "rev-parse", "HEAD"
        ], cwd=repo_dir)
        
        if success:
            commit_hash = stdout.strip()
            self.log(f"📝 Commit: {commit_hash}", Colors.BLUE)
        
        return repo_dir
    
    def install_dependencies(self, repo_dir: Path, env: Dict[str, str]) -> bool:
        """Install Python and Node.js dependencies"""
        self.log("📦 Installing dependencies...", Colors.BLUE, bold=True)
        
        # Create virtual environment
        venv_dir = repo_dir / "build-venv"
        self.log("Creating Python virtual environment...", Colors.BLUE)
        
        success, stdout, stderr = self.run_command([
            "python3", "-m", "venv", str(venv_dir)
        ], env=env)
        
        if not success:
            self.log(f"❌ Failed to create virtual environment: {stderr}", Colors.RED)
            return False
        
        # Activate virtual environment
        if platform.system() == "Windows":
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"
        
        # Upgrade pip
        self.log("Upgrading pip...", Colors.BLUE)
        success, stdout, stderr = self.run_command([
            str(pip_exe), "install", "--upgrade", "pip", "setuptools", "wheel"
        ], cwd=repo_dir, env=env)
        
        if not success:
            self.log(f"⚠️  Failed to upgrade pip: {stderr}", Colors.YELLOW)
        
        # Install Python dependencies
        requirements_file = repo_dir / "requirements.txt"
        if requirements_file.exists():
            self.log("Installing Python dependencies...", Colors.BLUE)
            success, stdout, stderr = self.run_command([
                str(pip_exe), "install", "-r", "requirements.txt"
            ], cwd=repo_dir, env=env, timeout=600)
            
            if not success:
                self.log(f"❌ Failed to install Python dependencies: {stderr}", Colors.RED)
                return False
            
            self.log("✅ Python dependencies installed", Colors.GREEN)
        
        # Install Node.js dependencies if frontend exists
        frontend_dir = repo_dir / "src" / "frontend"
        if frontend_dir.exists() and shutil.which("npm"):
            self.log("Installing Node.js dependencies...", Colors.BLUE)
            
            success, stdout, stderr = self.run_command([
                "npm", "ci"
            ], cwd=frontend_dir, env=env, timeout=600)
            
            if not success:
                self.log(f"❌ Failed to install Node.js dependencies: {stderr}", Colors.RED)
                return False
            
            self.log("✅ Node.js dependencies installed", Colors.GREEN)
        
        return True
    
    def build_frontend(self, repo_dir: Path, env: Dict[str, str]) -> bool:
        """Build frontend if it exists"""
        frontend_dir = repo_dir / "src" / "frontend"
        
        if not frontend_dir.exists():
            self.log("ℹ️  No frontend directory found, skipping frontend build", Colors.BLUE)
            return True
        
        if not shutil.which("npm"):
            self.log("⚠️  npm not found, skipping frontend build", Colors.YELLOW)
            return True
        
        self.log("🏗️  Building frontend...", Colors.BLUE, bold=True)
        
        success, stdout, stderr = self.run_command([
            "npm", "run", "build"
        ], cwd=frontend_dir, env=env, timeout=600)
        
        if not success:
            self.log(f"❌ Frontend build failed: {stderr}", Colors.RED)
            return False
        
        # Verify build output
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists():
            file_count = len(list(dist_dir.rglob("*")))
            self.log(f"✅ Frontend built successfully ({file_count} files)", Colors.GREEN)
        else:
            self.log("⚠️  Frontend build completed but no dist directory found", Colors.YELLOW)
        
        return True
    
    def build_installers(self, repo_dir: Path, version: str, platforms: List[str], 
                        env: Dict[str, str]) -> Dict[str, bool]:
        """Build installers for specified platforms"""
        self.log("🏗️  Building installers...", Colors.CYAN, bold=True)
        
        results = {}
        
        # Use virtual environment python
        venv_dir = repo_dir / "build-venv"
        if platform.system() == "Windows":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        
        for target_platform in platforms:
            self.log(f"Building {target_platform} installer...", Colors.BLUE)
            
            # Check if we can build for this platform
            current_platform = platform.system().lower()
            if target_platform == "macos" and current_platform != "darwin":
                self.log(f"⚠️  Cannot build macOS installer on {current_platform}", Colors.YELLOW)
                results[target_platform] = False
                continue
            
            if target_platform == "windows" and current_platform != "windows" and not shutil.which("makensis"):
                self.log(f"⚠️  Cannot build Windows installer without NSIS", Colors.YELLOW)
                results[target_platform] = False
                continue
            
            # Build installer
            build_script = repo_dir / "scripts" / "create-distribution.py"
            if not build_script.exists():
                # Try alternative script locations
                alt_scripts = [
                    repo_dir / "build.py",
                    repo_dir / "scripts" / "build.py"
                ]
                
                for alt_script in alt_scripts:
                    if alt_script.exists():
                        build_script = alt_script
                        break
                else:
                    self.log(f"❌ Build script not found", Colors.RED)
                    results[target_platform] = False
                    continue
            
            version_arg = version.lstrip('v') if version != "dev" else "dev"
            
            success, stdout, stderr = self.run_command([
                str(python_exe), str(build_script),
                "--platform", target_platform,
                "--version", version_arg
            ], cwd=repo_dir, env=env, timeout=1800)  # 30 minute timeout
            
            if success:
                self.log(f"✅ {target_platform} installer built successfully", Colors.GREEN)
                results[target_platform] = True
            else:
                self.log(f"❌ {target_platform} installer build failed: {stderr}", Colors.RED)
                results[target_platform] = False
        
        return results
    
    def generate_checksums(self, repo_dir: Path) -> bool:
        """Generate checksums for built installers"""
        self.log("🔐 Generating checksums...", Colors.BLUE)
        
        dist_dir = repo_dir / "distribution"
        if not dist_dir.exists():
            self.log("❌ Distribution directory not found", Colors.RED)
            return False
        
        # Find installer files
        installer_extensions = ['.exe', '.dmg', '.deb', '.rpm', '.AppImage']
        installer_files = []
        
        for ext in installer_extensions:
            installer_files.extend(dist_dir.rglob(f"*{ext}"))
        
        if not installer_files:
            self.log("❌ No installer files found", Colors.RED)
            return False
        
        # Generate checksums
        checksums = []
        for file_path in installer_files:
            self.log(f"Calculating checksum for {file_path.name}...", Colors.BLUE)
            
            import hashlib
            sha256_hash = hashlib.sha256()
            
            try:
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                
                checksum = sha256_hash.hexdigest().lower()
                relative_path = file_path.relative_to(dist_dir)
                checksums.append(f"{checksum}  {relative_path}")
                
            except Exception as e:
                self.log(f"❌ Failed to calculate checksum for {file_path.name}: {e}", Colors.RED)
                return False
        
        # Write checksums file
        checksums_file = dist_dir / "SHA256SUMS"
        try:
            with open(checksums_file, 'w') as f:
                f.write('\n'.join(checksums) + '\n')
            
            self.log(f"✅ Checksums written to {checksums_file}", Colors.GREEN)
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to write checksums file: {e}", Colors.RED)
            return False
    
    def generate_build_report(self, repo_dir: Path, version: str, platforms: List[str], 
                            build_results: Dict[str, bool], start_time: float) -> str:
        """Generate comprehensive build report"""
        duration = time.time() - start_time
        
        # Get system information
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
        }
        
        # Get tool versions
        tools = ["git", "python3", "node", "npm"]
        tool_versions = {}
        for tool in tools:
            if shutil.which(tool):
                success, stdout, stderr = self.run_command([tool, "--version"])
                if success:
                    tool_versions[tool] = stdout.strip().split('\n')[0]
        
        # Get commit information
        success, stdout, stderr = self.run_command([
            "git", "rev-parse", "HEAD"
        ], cwd=repo_dir)
        commit_hash = stdout.strip() if success else "unknown"
        
        # Count built files
        dist_dir = repo_dir / "distribution"
        built_files = []
        if dist_dir.exists():
            installer_extensions = ['.exe', '.dmg', '.deb', '.rpm', '.AppImage']
            for ext in installer_extensions:
                built_files.extend(dist_dir.rglob(f"*{ext}"))
        
        # Generate report
        report_lines = [
            "# Bitcoin Solo Miner Monitor - Build Report",
            f"**Generated**: {datetime.utcnow().isoformat()}Z",
            f"**Version**: {version}",
            f"**Commit**: {commit_hash}",
            f"**Build Duration**: {duration:.2f} seconds",
            "",
            "## System Information",
            f"- **Platform**: {system_info['platform']}",
            f"- **Python**: {system_info['python_version']}",
            f"- **Architecture**: {system_info['architecture'][0]}",
            f"- **Machine**: {system_info['machine']}",
            "",
            "## Tool Versions",
        ]
        
        for tool, version_info in tool_versions.items():
            report_lines.append(f"- **{tool}**: {version_info}")
        
        report_lines.extend([
            "",
            "## Build Results",
        ])
        
        successful_builds = 0
        for platform_name, success in build_results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            report_lines.append(f"- **{platform_name}**: {status}")
            if success:
                successful_builds += 1
        
        report_lines.extend([
            "",
            f"**Summary**: {successful_builds}/{len(build_results)} platforms built successfully",
            "",
            "## Built Files",
        ])
        
        if built_files:
            for file_path in built_files:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                report_lines.append(f"- **{file_path.name}**: {size_mb:.2f} MB")
        else:
            report_lines.append("- No installer files generated")
        
        return '\n'.join(report_lines)

def main():
    parser = argparse.ArgumentParser(
        description="Build Bitcoin Solo Miner Monitor installers from source",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build all platforms for a specific version
  python3 build-from-source.py --version v1.0.0 --platform all
  
  # Build Windows installer only
  python3 build-from-source.py --version v1.0.0 --platform windows
  
  # Development build from current branch
  python3 build-from-source.py --version dev --platform linux --dev-mode
  
  # Build with custom work directory
  python3 build-from-source.py --version v1.0.0 --platform all --work-dir ./build
        """
    )
    
    parser.add_argument(
        "--version",
        required=True,
        help="Version to build (e.g., v1.0.0 or 'dev' for current branch)"
    )
    
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        default="all",
        help="Platform(s) to build for"
    )
    
    parser.add_argument(
        "--work-dir",
        help="Working directory for build (default: temporary directory)"
    )
    
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep build files after completion"
    )
    
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Development mode (skip some checks, allow dirty working tree)"
    )
    
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Skip frontend build"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine platforms to build
    if args.platform == "all":
        platforms = ["windows", "macos", "linux"]
    else:
        platforms = [args.platform]
    
    # Create work directory
    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="bitcoin-miner-build-"))
    
    build_env = BuildEnvironment(work_dir)
    start_time = time.time()
    
    try:
        build_env.log(f"🚀 Starting build of Bitcoin Solo Miner Monitor {args.version}", 
                     Colors.MAGENTA, bold=True)
        build_env.log(f"Working directory: {work_dir}", Colors.BLUE)
        build_env.log(f"Target platforms: {', '.join(platforms)}", Colors.BLUE)
        
        # Check prerequisites
        if not args.dev_mode and not build_env.check_prerequisites():
            sys.exit(1)
        
        # Set up reproducible environment
        env = build_env.setup_reproducible_environment()
        
        # Clone repository
        repo_dir = build_env.clone_repository(args.version)
        
        # Install dependencies
        if not build_env.install_dependencies(repo_dir, env):
            sys.exit(1)
        
        # Build frontend
        if not args.no_frontend and not build_env.build_frontend(repo_dir, env):
            sys.exit(1)
        
        # Build installers
        build_results = build_env.build_installers(repo_dir, args.version, platforms, env)
        
        # Generate checksums
        if any(build_results.values()):
            build_env.generate_checksums(repo_dir)
        
        # Generate build report
        report_content = build_env.generate_build_report(
            repo_dir, args.version, platforms, build_results, start_time
        )
        
        report_file = work_dir / f"build-report-{args.version}-{int(time.time())}.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        build_env.log(f"📄 Build report saved to: {report_file}", Colors.BLUE)
        
        # Print summary
        successful_builds = sum(1 for success in build_results.values() if success)
        total_builds = len(build_results)
        
        if successful_builds == total_builds:
            build_env.log(f"🎉 All {total_builds} builds completed successfully!", 
                         Colors.GREEN, bold=True)
            
            # Show built files
            dist_dir = repo_dir / "distribution"
            if dist_dir.exists():
                build_env.log("📦 Built files:", Colors.BLUE)
                installer_extensions = ['.exe', '.dmg', '.deb', '.rpm', '.AppImage']
                for ext in installer_extensions:
                    for file_path in dist_dir.rglob(f"*{ext}"):
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        build_env.log(f"  {file_path.name} ({size_mb:.2f} MB)", Colors.CYAN)
        else:
            build_env.log(f"⚠️  {successful_builds}/{total_builds} builds completed successfully", 
                         Colors.YELLOW, bold=True)
        
        # Cleanup if requested
        if not args.keep_files and not args.work_dir:
            shutil.rmtree(work_dir)
            build_env.log("🧹 Cleaned up temporary files", Colors.BLUE)
        else:
            build_env.log(f"📁 Build files kept in: {work_dir}", Colors.BLUE)
        
        # Exit with appropriate code
        sys.exit(0 if successful_builds == total_builds else 1)
        
    except KeyboardInterrupt:
        build_env.log("\n⚠️  Build interrupted by user", Colors.YELLOW)
        sys.exit(130)
    except Exception as e:
        build_env.log(f"\n❌ Build failed with error: {e}", Colors.RED)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()