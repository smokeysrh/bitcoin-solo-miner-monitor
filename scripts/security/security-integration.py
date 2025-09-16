#!/usr/bin/env python3
"""
Security Integration Script
Integrates security scanning, vulnerability detection, and patch distribution
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from .installer_security_scanner import SecurityScanner
    from .vulnerability_detector import VulnerabilityDetector
    from .security_patch_distributor import SecurityPatchDistributor
except ImportError:
    # Fallback for direct execution
    import importlib.util
    import sys
    
    def load_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    base_dir = Path(__file__).parent
    scanner_module = load_module_from_file("installer_security_scanner", base_dir / "installer-security-scanner.py")
    detector_module = load_module_from_file("vulnerability_detector", base_dir / "vulnerability-detector.py")
    distributor_module = load_module_from_file("security_patch_distributor", base_dir / "security-patch-distributor.py")
    
    SecurityScanner = scanner_module.SecurityScanner
    VulnerabilityDetector = detector_module.VulnerabilityDetector
    SecurityPatchDistributor = distributor_module.SecurityPatchDistributor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityIntegration:
    """Main security integration system"""
    
    def __init__(self, config_file: str = "config/security-config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.output_dir = Path("security-reports")
        self.output_dir.mkdir(exist_ok=True)
        
    def _load_config(self) -> Dict:
        """Load security configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
                
        # Return default configuration
        return {
            "vulnerability_scanning": {"enabled": True},
            "installer_security": {"enabled": True},
            "patch_verification": {"enabled": True}
        }
        
    def run_complete_security_scan(self, installer_files: List[str] = None, 
                                 current_version: str = None) -> Dict:
        """Run complete security scan including all components"""
        logger.info("[SECURITY] Starting complete security scan...")
        
        results = {
            "scan_timestamp": datetime.now().isoformat(),
            "vulnerability_scan": None,
            "installer_scan": None,
            "patch_check": None,
            "overall_status": "unknown",
            "critical_issues": [],
            "recommendations": []
        }
        
        # 1. Vulnerability Detection
        if self.config.get("vulnerability_scanning", {}).get("enabled", True):
            logger.info("🔍 Running vulnerability detection...")
            try:
                detector = VulnerabilityDetector()
                
                # Scan all dependency types
                scan_results = []
                
                # Python dependencies
                python_result = detector.scan_python_dependencies("requirements.txt")
                scan_results.append(python_result)
                
                # Node.js dependencies
                nodejs_result = detector.scan_nodejs_dependencies("src/frontend")
                scan_results.append(nodejs_result)
                
                # System dependencies
                system_result = detector.scan_system_dependencies()
                scan_results.append(system_result)
                
                # Generate vulnerability report
                vuln_report = detector.generate_vulnerability_report(scan_results, str(self.output_dir))
                results["vulnerability_scan"] = {
                    "success": True,
                    "report_file": vuln_report,
                    "scan_results": scan_results
                }
                
                # Check for critical vulnerabilities
                total_critical = sum(r.get("summary", {}).get("high", 0) for r in scan_results)
                if total_critical > 0:
                    results["critical_issues"].append(f"{total_critical} critical vulnerabilities found")
                    
            except Exception as e:
                logger.error(f"Vulnerability detection failed: {e}")
                results["vulnerability_scan"] = {"success": False, "error": str(e)}
                
        # 2. Installer Security Scanning
        if installer_files and self.config.get("installer_security", {}).get("enabled", True):
            logger.info("📦 Running installer security scanning...")
            try:
                scanner = SecurityScanner(str(self.output_dir))
                installer_results = []
                
                for installer_file in installer_files:
                    if Path(installer_file).exists():
                        scan_result = scanner.scan_installer_file(installer_file)
                        installer_results.append(scan_result)
                        
                        if scan_result["overall_status"] == "fail":
                            results["critical_issues"].append(f"Installer {Path(installer_file).name} failed security checks")
                            
                if installer_results:
                    installer_report = scanner.generate_report(installer_results, "markdown")
                    results["installer_scan"] = {
                        "success": True,
                        "report_file": installer_report,
                        "scan_results": installer_results
                    }
                else:
                    results["installer_scan"] = {"success": False, "error": "No installer files found"}
                    
            except Exception as e:
                logger.error(f"Installer security scanning failed: {e}")
                results["installer_scan"] = {"success": False, "error": str(e)}
                
        # 3. Security Patch Check
        if current_version and self.config.get("patch_verification", {}).get("enabled", True):
            logger.info("🔄 Checking for security patches...")
            try:
                distributor = SecurityPatchDistributor(str(self.config_file))
                patch_result = distributor.check_for_security_updates(current_version)
                
                results["patch_check"] = {
                    "success": True,
                    "update_result": patch_result
                }
                
                if patch_result["critical_updates"]:
                    results["critical_issues"].append(f"{len(patch_result['critical_updates'])} critical security updates available")
                    
            except Exception as e:
                logger.error(f"Security patch check failed: {e}")
                results["patch_check"] = {"success": False, "error": str(e)}
                
        # Determine overall status
        results["overall_status"] = self._determine_overall_status(results)
        
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)
        
        # Generate consolidated report
        self._generate_consolidated_report(results)
        
        return results
        
    def _determine_overall_status(self, results: Dict) -> str:
        """Determine overall security status"""
        if results["critical_issues"]:
            return "critical"
            
        # Check individual scan results
        if results.get("vulnerability_scan", {}).get("success") is False:
            return "warning"
        if results.get("installer_scan", {}).get("success") is False:
            return "warning"
        if results.get("patch_check", {}).get("success") is False:
            return "warning"
            
        # Check for any security issues
        vuln_scan = results.get("vulnerability_scan", {}).get("scan_results", [])
        if any(r.get("summary", {}).get("total", 0) > 0 for r in vuln_scan):
            return "warning"
            
        installer_scan = results.get("installer_scan", {}).get("scan_results", [])
        if any(r.get("overall_status") in ["fail", "warning"] for r in installer_scan):
            return "warning"
            
        patch_check = results.get("patch_check", {}).get("update_result", {})
        if patch_check.get("security_updates"):
            return "warning"
            
        return "pass"
        
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if results["critical_issues"]:
            recommendations.append("🚨 Address critical security issues immediately before release")
            
        # Vulnerability-specific recommendations
        vuln_scan = results.get("vulnerability_scan", {}).get("scan_results", [])
        total_vulns = sum(r.get("summary", {}).get("total", 0) for r in vuln_scan)
        if total_vulns > 0:
            recommendations.append(f"Update {total_vulns} vulnerable dependencies")
            
        # Installer-specific recommendations
        installer_scan = results.get("installer_scan", {}).get("scan_results", [])
        failed_installers = [r for r in installer_scan if r.get("overall_status") == "fail"]
        if failed_installers:
            recommendations.append(f"Fix security issues in {len(failed_installers)} installer(s)")
            
        # Patch-specific recommendations
        patch_check = results.get("patch_check", {}).get("update_result", {})
        if patch_check.get("critical_updates"):
            recommendations.append("Apply critical security patches immediately")
        elif patch_check.get("security_updates"):
            recommendations.append("Schedule security updates for next maintenance window")
            
        # General recommendations
        recommendations.extend([
            "Enable automated security scanning in CI/CD pipeline",
            "Set up security monitoring and alerting",
            "Regularly review and update security policies",
            "Maintain security documentation for community"
        ])
        
        return recommendations
        
    def _generate_consolidated_report(self, results: Dict) -> str:
        """Generate consolidated security report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"consolidated_security_report_{timestamp}.md"
        
        lines = [
            "# Consolidated Security Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            ""
        ]
        
        status_emoji = {
            "pass": "✅",
            "warning": "⚠️",
            "critical": "🚨"
        }.get(results["overall_status"], "❓")
        
        lines.extend([
            f"**Overall Status:** {status_emoji} {results['overall_status'].upper()}",
            ""
        ])
        
        if results["critical_issues"]:
            lines.extend([
                "### Critical Issues",
                ""
            ])
            for issue in results["critical_issues"]:
                lines.append(f"- 🚨 {issue}")
            lines.append("")
            
        # Vulnerability Scan Results
        if results.get("vulnerability_scan"):
            lines.extend([
                "## Vulnerability Scan Results",
                ""
            ])
            
            if results["vulnerability_scan"]["success"]:
                scan_results = results["vulnerability_scan"]["scan_results"]
                total_vulns = sum(r.get("summary", {}).get("total", 0) for r in scan_results)
                
                if total_vulns == 0:
                    lines.append("✅ No vulnerabilities detected in dependencies")
                else:
                    lines.append(f"⚠️ {total_vulns} vulnerabilities detected across all dependencies")
                    
                lines.extend([
                    "",
                    f"**Detailed Report:** {results['vulnerability_scan']['report_file']}",
                    ""
                ])
            else:
                lines.extend([
                    f"❌ Vulnerability scan failed: {results['vulnerability_scan'].get('error', 'Unknown error')}",
                    ""
                ])
                
        # Installer Scan Results
        if results.get("installer_scan"):
            lines.extend([
                "## Installer Security Scan Results",
                ""
            ])
            
            if results["installer_scan"]["success"]:
                scan_results = results["installer_scan"]["scan_results"]
                failed_count = len([r for r in scan_results if r.get("overall_status") == "fail"])
                warning_count = len([r for r in scan_results if r.get("overall_status") == "warning"])
                
                if failed_count == 0 and warning_count == 0:
                    lines.append("✅ All installers passed security checks")
                else:
                    lines.append(f"⚠️ {failed_count} installers failed, {warning_count} have warnings")
                    
                lines.extend([
                    "",
                    f"**Detailed Report:** {results['installer_scan']['report_file']}",
                    ""
                ])
            else:
                lines.extend([
                    f"❌ Installer scan failed: {results['installer_scan'].get('error', 'Unknown error')}",
                    ""
                ])
                
        # Security Patch Check Results
        if results.get("patch_check"):
            lines.extend([
                "## Security Patch Check Results",
                ""
            ])
            
            if results["patch_check"]["success"]:
                update_result = results["patch_check"]["update_result"]
                critical_count = len(update_result.get("critical_updates", []))
                total_count = len(update_result.get("security_updates", []))
                
                if total_count == 0:
                    lines.append("✅ No security updates available")
                else:
                    lines.append(f"⚠️ {total_count} security updates available ({critical_count} critical)")
                    
                lines.append("")
            else:
                lines.extend([
                    f"❌ Patch check failed: {results['patch_check'].get('error', 'Unknown error')}",
                    ""
                ])
                
        # Recommendations
        if results["recommendations"]:
            lines.extend([
                "## Recommendations",
                ""
            ])
            
            for rec in results["recommendations"]:
                lines.append(f"- {rec}")
                
        lines.extend([
            "",
            "---",
            "",
            "*This report was generated by the Bitcoin Solo Miner Monitor security integration system.*"
        ])
        
        with open(report_file, 'w') as f:
            f.write("\n".join(lines))
            
        logger.info(f"📄 Consolidated security report generated: {report_file}")
        return str(report_file)
        
    def setup_security_monitoring(self) -> Dict:
        """Set up security monitoring and alerting"""
        result = {
            "monitoring_setup": False,
            "config_created": False,
            "integration_status": "pending"
        }
        
        try:
            # Create monitoring configuration
            monitoring_config = {
                "enabled": True,
                "check_interval_minutes": 60,
                "alert_thresholds": {
                    "critical_vulnerabilities": 1,
                    "high_vulnerabilities": 5,
                    "failed_installers": 1
                },
                "notification_channels": [
                    {
                        "type": "log",
                        "enabled": True,
                        "level": "warning"
                    }
                ]
            }
            
            monitoring_file = Path("config/security-monitoring.json")
            monitoring_file.parent.mkdir(exist_ok=True)
            
            with open(monitoring_file, 'w') as f:
                json.dump(monitoring_config, f, indent=2)
                
            result["config_created"] = True
            result["monitoring_setup"] = True
            
            logger.info(f"[SUCCESS] Security monitoring configured: {monitoring_file}")
            
        except Exception as e:
            logger.error(f"Failed to setup security monitoring: {e}")
            
        return result


def main():
    parser = argparse.ArgumentParser(description="Security integration system")
    parser.add_argument("--scan-all", action="store_true", help="Run complete security scan")
    parser.add_argument("--installer-files", nargs="*", help="Installer files to scan")
    parser.add_argument("--current-version", help="Current application version")
    parser.add_argument("--setup-monitoring", action="store_true", help="Setup security monitoring")
    parser.add_argument("--config", help="Path to security configuration file")
    parser.add_argument("--output-dir", default="security-reports", help="Output directory for reports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    config_file = args.config if args.config else "config/security-config.json"
    integration = SecurityIntegration(config_file)
    
    if args.setup_monitoring:
        monitoring_result = integration.setup_security_monitoring()
        if monitoring_result["monitoring_setup"]:
            print("[SUCCESS] Security monitoring setup completed")
        else:
            print("[FAIL] Security monitoring setup failed")
            
    if args.scan_all:
        logger.info("🔒 Running complete security scan...")
        
        results = integration.run_complete_security_scan(
            installer_files=args.installer_files,
            current_version=args.current_version
        )
        
        # Print summary
        status_emoji = {
            "pass": "✅",
            "warning": "⚠️",
            "critical": "🚨"
        }.get(results["overall_status"], "❓")
        
        print(f"\n{status_emoji} Overall Security Status: {results['overall_status'].upper()}")
        
        if results["critical_issues"]:
            print(f"\n🚨 Critical Issues ({len(results['critical_issues'])}):")
            for issue in results["critical_issues"]:
                print(f"  - {issue}")
                
        if results["recommendations"]:
            print(f"\n📋 Recommendations ({len(results['recommendations'])}):")
            for i, rec in enumerate(results["recommendations"][:5], 1):  # Show top 5
                print(f"  {i}. {rec}")
                
        # Exit with appropriate code
        if results["overall_status"] == "critical":
            sys.exit(1)
        elif results["overall_status"] == "warning":
            sys.exit(2)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()