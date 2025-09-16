#!/usr/bin/env python3
"""
Security Patch Distribution System
Manages security patch distribution through the application's update mechanism
"""

import os
import sys
import json
import requests
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import tempfile
import shutil
from packaging import version

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityPatchDistributor:
    """Manages security patch distribution and updates"""
    
    def __init__(self, config_file: str = "security-config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.patch_cache = Path(".security-patches")
        self.patch_cache.mkdir(exist_ok=True)
        
    def _load_config(self) -> Dict:
        """Load security configuration"""
        default_config = {
            "github_repo": "bitcoin-solo-miner/monitor",
            "security_branch": "security-patches",
            "update_server_url": "https://api.github.com/repos/bitcoin-solo-miner/monitor",
            "patch_check_interval_hours": 6,
            "auto_apply_critical": False,
            "notification_channels": [],
            "trusted_signers": [],
            "patch_verification": {
                "require_signature": False,
                "require_checksum": True,
                "require_community_review": True
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
                
        return default_config
        
    def check_for_security_updates(self, current_version: str) -> Dict:
        """Check for available security updates"""
        logger.info(f"🔍 Checking for security updates (current version: {current_version})")
        
        result = {
            "current_version": current_version,
            "check_timestamp": datetime.now().isoformat(),
            "security_updates": [],
            "critical_updates": [],
            "recommended_action": "none"
        }
        
        try:
            # Check GitHub releases for security updates
            releases = self._fetch_github_releases()
            
            for release in releases:
                release_version = release.get("tag_name", "").lstrip("v")
                
                # Skip if this is not a newer version
                if not self._is_newer_version(release_version, current_version):
                    continue
                    
                # Check if this is a security release
                security_info = self._analyze_security_release(release)
                
                if security_info["is_security_release"]:
                    update_info = {
                        "version": release_version,
                        "release_date": release.get("published_at"),
                        "security_level": security_info["security_level"],
                        "cve_ids": security_info["cve_ids"],
                        "description": release.get("body", ""),
                        "download_url": self._get_download_url(release),
                        "checksum": self._get_release_checksum(release),
                        "verification_status": "pending"
                    }
                    
                    result["security_updates"].append(update_info)
                    
                    if security_info["security_level"] == "critical":
                        result["critical_updates"].append(update_info)
                        
            # Determine recommended action
            if result["critical_updates"]:
                result["recommended_action"] = "immediate_update"
            elif result["security_updates"]:
                result["recommended_action"] = "scheduled_update"
                
        except Exception as e:
            logger.error(f"Failed to check for security updates: {e}")
            result["error"] = str(e)
            
        return result
        
    def _fetch_github_releases(self) -> List[Dict]:
        """Fetch releases from GitHub API"""
        url = f"{self.config['update_server_url']}/releases"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GitHub releases: {e}")
            return []
            
    def _is_newer_version(self, release_version: str, current_version: str) -> bool:
        """Check if release version is newer than current version"""
        try:
            return version.parse(release_version) > version.parse(current_version)
        except Exception:
            # Fallback to string comparison if version parsing fails
            return release_version > current_version
            
    def _analyze_security_release(self, release: Dict) -> Dict:
        """Analyze if a release contains security fixes"""
        release_body = release.get("body", "").lower()
        release_name = release.get("name", "").lower()
        
        security_keywords = [
            "security", "vulnerability", "cve-", "exploit", "patch",
            "fix", "critical", "urgent", "hotfix", "security fix"
        ]
        
        cve_pattern = r'cve-\d{4}-\d{4,}'
        
        is_security = any(keyword in release_body or keyword in release_name 
                         for keyword in security_keywords)
        
        # Extract CVE IDs
        import re
        cve_ids = re.findall(cve_pattern, release_body, re.IGNORECASE)
        
        # Determine security level
        security_level = "low"
        if any(word in release_body for word in ["critical", "urgent", "immediate"]):
            security_level = "critical"
        elif any(word in release_body for word in ["high", "important", "severe"]):
            security_level = "high"
        elif any(word in release_body for word in ["medium", "moderate"]):
            security_level = "medium"
            
        return {
            "is_security_release": is_security,
            "security_level": security_level,
            "cve_ids": cve_ids
        }
        
    def _get_download_url(self, release: Dict) -> Optional[str]:
        """Get download URL for the appropriate platform"""
        assets = release.get("assets", [])
        
        # Determine current platform
        import platform
        system = platform.system().lower()
        
        # Platform-specific asset patterns
        patterns = {
            "windows": [".exe", "windows", "win"],
            "darwin": [".dmg", "macos", "mac", "darwin"],
            "linux": [".deb", ".rpm", ".appimage", "linux"]
        }
        
        if system in patterns:
            for asset in assets:
                asset_name = asset.get("name", "").lower()
                if any(pattern in asset_name for pattern in patterns[system]):
                    return asset.get("browser_download_url")
                    
        # Fallback to source code
        return release.get("zipball_url")
        
    def _get_release_checksum(self, release: Dict) -> Optional[str]:
        """Get checksum for release verification"""
        assets = release.get("assets", [])
        
        # Look for checksum files
        for asset in assets:
            asset_name = asset.get("name", "").lower()
            if any(name in asset_name for name in ["sha256", "checksum", "hash"]):
                try:
                    checksum_url = asset.get("browser_download_url")
                    response = requests.get(checksum_url, timeout=30)
                    response.raise_for_status()
                    return response.text.strip()
                except Exception as e:
                    logger.warning(f"Could not fetch checksum: {e}")
                    
        return None
        
    def download_security_patch(self, update_info: Dict, output_dir: str = None) -> Dict:
        """Download and verify a security patch"""
        if not output_dir:
            output_dir = self.patch_cache
        else:
            output_dir = Path(output_dir)
            
        output_dir.mkdir(exist_ok=True)
        
        logger.info(f"📥 Downloading security patch for version {update_info['version']}")
        
        result = {
            "version": update_info["version"],
            "download_timestamp": datetime.now().isoformat(),
            "download_success": False,
            "verification_success": False,
            "file_path": None,
            "errors": []
        }
        
        try:
            download_url = update_info["download_url"]
            if not download_url:
                raise ValueError("No download URL available")
                
            # Download the file
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Determine filename
            filename = self._extract_filename_from_url(download_url)
            if not filename:
                filename = f"security-patch-{update_info['version']}"
                
            file_path = output_dir / filename
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log every MB
                                logger.info(f"📥 Downloaded {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB ({progress:.1f}%)")
                                
            result["download_success"] = True
            result["file_path"] = str(file_path)
            
            # Verify the download
            verification_result = self._verify_patch_file(file_path, update_info)
            result["verification_success"] = verification_result["success"]
            
            if not verification_result["success"]:
                result["errors"].extend(verification_result["errors"])
                
        except Exception as e:
            logger.error(f"Failed to download security patch: {e}")
            result["errors"].append(str(e))
            
        return result
        
    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """Extract filename from download URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return Path(parsed.path).name
        except Exception:
            return None
            
    def _verify_patch_file(self, file_path: Path, update_info: Dict) -> Dict:
        """Verify downloaded patch file"""
        result = {"success": True, "errors": []}
        
        try:
            # Verify file exists and is readable
            if not file_path.exists():
                result["errors"].append("Downloaded file does not exist")
                result["success"] = False
                return result
                
            # Verify checksum if available
            expected_checksum = update_info.get("checksum")
            if expected_checksum and self.config["patch_verification"]["require_checksum"]:
                actual_checksum = self._calculate_file_checksum(file_path)
                
                if expected_checksum.lower() != actual_checksum.lower():
                    result["errors"].append("Checksum verification failed")
                    result["success"] = False
                    
            # Verify file size is reasonable
            file_size = file_path.stat().st_size
            if file_size < 1024:  # Less than 1KB is suspicious
                result["errors"].append("Downloaded file is suspiciously small")
                result["success"] = False
            elif file_size > 1024 * 1024 * 1024:  # More than 1GB is suspicious
                result["errors"].append("Downloaded file is suspiciously large")
                result["success"] = False
                
        except Exception as e:
            result["errors"].append(f"Verification failed: {str(e)}")
            result["success"] = False
            
        return result
        
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
                
        return sha256_hash.hexdigest()
        
    def create_security_notification(self, security_updates: List[Dict]) -> Dict:
        """Create security notification for users"""
        notification = {
            "timestamp": datetime.now().isoformat(),
            "type": "security_update",
            "priority": "normal",
            "title": "Security Updates Available",
            "message": "",
            "updates": security_updates,
            "actions": []
        }
        
        critical_updates = [u for u in security_updates if u.get("security_level") == "critical"]
        
        if critical_updates:
            notification["priority"] = "critical"
            notification["title"] = "Critical Security Updates Available"
            notification["message"] = f"Critical security updates are available for {len(critical_updates)} vulnerabilities. Immediate update recommended."
            notification["actions"] = [
                {"type": "update_now", "label": "Update Now"},
                {"type": "view_details", "label": "View Details"},
                {"type": "remind_later", "label": "Remind in 1 Hour"}
            ]
        else:
            notification["message"] = f"Security updates are available for {len(security_updates)} issues. Update when convenient."
            notification["actions"] = [
                {"type": "update_now", "label": "Update Now"},
                {"type": "view_details", "label": "View Details"},
                {"type": "schedule_update", "label": "Schedule Update"},
                {"type": "dismiss", "label": "Dismiss"}
            ]
            
        return notification
        
    def generate_security_advisory(self, security_updates: List[Dict], output_dir: str = "security-reports") -> str:
        """Generate security advisory document"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        advisory_file = output_path / f"security_advisory_{timestamp}.md"
        
        lines = [
            "# Security Advisory",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Advisory ID:** BTCSM-{timestamp}",
            "",
            "## Summary",
            ""
        ]
        
        critical_count = len([u for u in security_updates if u.get("security_level") == "critical"])
        high_count = len([u for u in security_updates if u.get("security_level") == "high"])
        
        if critical_count > 0:
            lines.extend([
                f"🚨 **CRITICAL:** {critical_count} critical security vulnerabilities have been identified.",
                "**Immediate action required.**",
                ""
            ])
        elif high_count > 0:
            lines.extend([
                f"⚠️ **HIGH:** {high_count} high-severity security vulnerabilities have been identified.",
                "**Update recommended as soon as possible.**",
                ""
            ])
        else:
            lines.extend([
                f"ℹ️ **MODERATE:** {len(security_updates)} security vulnerabilities have been identified.",
                "**Update recommended at your convenience.**",
                ""
            ])
            
        lines.extend([
            "## Affected Versions",
            "",
            "All versions prior to the latest security release are affected.",
            "",
            "## Security Updates",
            ""
        ])
        
        for i, update in enumerate(security_updates, 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠", 
                "medium": "🟡",
                "low": "🟢"
            }.get(update.get("security_level", "medium"), "⚪")
            
            lines.extend([
                f"### {i}. Version {update['version']} {severity_emoji}",
                f"**Severity:** {update.get('security_level', 'Unknown').title()}",
                f"**Release Date:** {update.get('release_date', 'Unknown')}",
                ""
            ])
            
            if update.get("cve_ids"):
                lines.extend([
                    f"**CVE IDs:** {', '.join(update['cve_ids'])}",
                    ""
                ])
                
            if update.get("description"):
                lines.extend([
                    "**Description:**",
                    update["description"],
                    ""
                ])
                
            lines.extend([
                f"**Download:** [Version {update['version']}]({update.get('download_url', '#')})",
                ""
            ])
            
        lines.extend([
            "## Update Instructions",
            "",
            "### Automatic Update (Recommended)",
            "",
            "1. Open Bitcoin Solo Miner Monitor",
            "2. Go to Settings > Updates",
            "3. Click 'Check for Updates'",
            "4. Follow the prompts to install security updates",
            "",
            "### Manual Update",
            "",
            "1. Download the latest version from the official GitHub releases",
            "2. Verify the SHA256 checksum",
            "3. Close the current application",
            "4. Install the new version",
            "5. Restart the application",
            "",
            "## Verification",
            "",
            "Always verify downloads using the provided SHA256 checksums:",
            ""
        ])
        
        for update in security_updates:
            if update.get("checksum"):
                lines.extend([
                    f"**Version {update['version']}:**",
                    f"```",
                    f"{update['checksum']}",
                    f"```",
                    ""
                ])
                
        lines.extend([
            "## Community Response",
            "",
            "This security advisory follows our commitment to transparent security practices.",
            "The Bitcoin Solo Miner Monitor project maintains:",
            "",
            "- Open source code for community review",
            "- Reproducible builds for verification",
            "- Prompt disclosure of security issues",
            "- Community-driven security improvements",
            "",
            "## Contact",
            "",
            "For questions about this security advisory:",
            "",
            "- GitHub Issues: https://github.com/bitcoin-solo-miner/monitor/issues",
            "- Security Email: security@bitcoin-solo-miner.org",
            "",
            "---",
            "",
            "*This advisory was generated automatically by the Bitcoin Solo Miner Monitor security system.*"
        ])
        
        with open(advisory_file, 'w') as f:
            f.write("\n".join(lines))
            
        logger.info(f"📄 Security advisory generated: {advisory_file}")
        return str(advisory_file)
        
    def integrate_with_update_system(self, app_config_path: str = None) -> Dict:
        """Integrate security patch distribution with the application's update system"""
        result = {
            "integration_success": False,
            "update_config_path": None,
            "errors": []
        }
        
        try:
            # Find application update configuration
            if not app_config_path:
                possible_paths = [
                    "src/backend/config/update_config.json",
                    "config/update_config.json", 
                    "update_config.json"
                ]
                
                for path in possible_paths:
                    if Path(path).exists():
                        app_config_path = path
                        break
                        
            if not app_config_path:
                # Create default update configuration
                app_config_path = "config/update_config.json"
                Path(app_config_path).parent.mkdir(exist_ok=True)
                
                default_update_config = {
                    "update_server_url": self.config["update_server_url"],
                    "check_interval_hours": 24,
                    "security_check_interval_hours": self.config["patch_check_interval_hours"],
                    "auto_download_security_updates": True,
                    "auto_apply_critical_updates": self.config["auto_apply_critical"],
                    "notification_settings": {
                        "show_security_notifications": True,
                        "show_update_notifications": True
                    }
                }
                
                with open(app_config_path, 'w') as f:
                    json.dump(default_update_config, f, indent=2)
                    
            result["update_config_path"] = app_config_path
            result["integration_success"] = True
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Failed to integrate with update system: {e}")
            
        return result


def main():
    parser = argparse.ArgumentParser(description="Security patch distribution system")
    parser.add_argument("--check-updates", action="store_true", help="Check for security updates")
    parser.add_argument("--current-version", required=True, help="Current application version")
    parser.add_argument("--download-patches", action="store_true", help="Download available security patches")
    parser.add_argument("--generate-advisory", action="store_true", help="Generate security advisory")
    parser.add_argument("--integrate-update-system", action="store_true", help="Integrate with application update system")
    parser.add_argument("--config", help="Path to security configuration file")
    parser.add_argument("--output-dir", default="security-reports", help="Output directory for reports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    config_file = args.config if args.config else "security-config.json"
    distributor = SecurityPatchDistributor(config_file)
    
    if args.check_updates:
        logger.info("🔍 Checking for security updates...")
        update_result = distributor.check_for_security_updates(args.current_version)
        
        print(f"Security updates found: {len(update_result['security_updates'])}")
        print(f"Critical updates: {len(update_result['critical_updates'])}")
        print(f"Recommended action: {update_result['recommended_action']}")
        
        if update_result["security_updates"]:
            # Generate notification
            notification = distributor.create_security_notification(update_result["security_updates"])
            print(f"\nNotification: {notification['title']}")
            print(f"Priority: {notification['priority']}")
            
            if args.generate_advisory:
                advisory_file = distributor.generate_security_advisory(
                    update_result["security_updates"], 
                    args.output_dir
                )
                print(f"Security advisory: {advisory_file}")
                
            if args.download_patches:
                for update in update_result["security_updates"]:
                    download_result = distributor.download_security_patch(update)
                    if download_result["download_success"]:
                        print(f"✅ Downloaded patch for version {update['version']}")
                    else:
                        print(f"❌ Failed to download patch for version {update['version']}")
                        
    if args.integrate_update_system:
        integration_result = distributor.integrate_with_update_system()
        if integration_result["integration_success"]:
            print(f"✅ Integrated with update system: {integration_result['update_config_path']}")
        else:
            print(f"❌ Integration failed: {integration_result['errors']}")


if __name__ == "__main__":
    main()