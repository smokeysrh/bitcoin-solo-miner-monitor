#!/usr/bin/env python3
"""
Cross-Platform Testing Automation Runner
Orchestrates comprehensive installer testing across all platforms and user scenarios
"""

import os
import sys
import json
import time
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CrossPlatformTestRunner:
    """Orchestrates comprehensive cross-platform installer testing"""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.test_dir = self.project_root / "tests" / "installer"
        
        # Import test modules
        sys.path.insert(0, str(self.test_dir))
        
        try:
            from test_cross_platform_automation import CrossPlatformTester
            from user_experience_simulator import UserExperienceSimulator
            from installation_success_monitor import InstallationSuccessMonitor
            
            self.cross_platform_tester = CrossPlatformTester(project_root)
            self.ux_simulator = UserExperienceSimulator(project_root)
            self.success_monitor = InstallationSuccessMonitor(project_root)
            
        except ImportError as e:
            logger.error(f"Failed to import test modules: {e}")
            sys.exit(1)
        
        # Test configuration
        self.config = {
            "test_types": {
                "integrity": True,
                "structure": True,
                "installation": True,
                "user_experience": True,
                "monitoring": True
            },
            "platforms": ["windows", "macos", "linux"],
            "installer_types": [".exe", ".dmg", ".deb", ".rpm", ".AppImage"],
            "timeout_minutes": 30,
            "retry_attempts": 2
        }
        
        # Initialize test session
        self.test_session = {
            "session_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "platform": platform.system().lower(),
            "test_results": {
                "cross_platform": None,
                "user_experience": None,
                "monitoring": None
            },
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "overall_success_rate": 0.0,
                "recommendations": []
            }
        }
    
    def find_installer_files(self, installer_dir: Optional[Path] = None) -> List[Path]:
        """Find all installer files to test"""
        if installer_dir is None:
            installer_dir = self.project_root / "distribution"
        
        if not installer_dir.exists():
            logger.warning(f"Distribution directory not found: {installer_dir}")
            return []
        
        installer_files = []
        for ext in self.config["installer_types"]:
            for file_path in installer_dir.rglob(f"*{ext}"):
                if file_path.is_file():
                    installer_files.append(file_path)
        
        logger.info(f"Found {len(installer_files)} installer files to test")
        return installer_files
    
    def run_cross_platform_tests(self, installer_files: List[Path]) -> Dict:
        """Run comprehensive cross-platform tests"""
        logger.info("🔧 Running cross-platform installer tests...")
        
        try:
            success = self.cross_platform_tester.run_comprehensive_test_suite(installer_files)
            
            # Get the test session results
            test_results = self.cross_platform_tester.test_session
            
            logger.info(f"✅ Cross-platform tests completed with {test_results['summary']['success_rate']:.1f}% success rate")
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Cross-platform tests failed: {e}")
            return {
                "error": str(e),
                "summary": {
                    "success_rate": 0.0,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 1
                }
            }
    
    def run_user_experience_tests(self, installer_files: List[Path]) -> Dict:
        """Run user experience simulation tests"""
        logger.info("🎭 Running user experience simulation tests...")
        
        try:
            results = self.ux_simulator.run_user_experience_tests(installer_files)
            
            logger.info(f"✅ UX tests completed with {results['summary']['user_satisfaction_score']:.1f}/10 satisfaction score")
            return results
            
        except Exception as e:
            logger.error(f"❌ User experience tests failed: {e}")
            return {
                "error": str(e),
                "summary": {
                    "user_satisfaction_score": 0.0,
                    "successful_installations": 0,
                    "total_personas": 0
                }
            }
    
    def run_monitoring_analysis(self) -> Dict:
        """Run installation success monitoring analysis"""
        logger.info("📊 Running installation success monitoring analysis...")
        
        try:
            # Import any existing test results first
            results_dir = self.test_dir / "results"
            if results_dir.exists():
                for results_file in results_dir.glob("test_report_*.json"):
                    try:
                        self.success_monitor.import_test_results(results_file)
                    except Exception as e:
                        logger.warning(f"Failed to import {results_file}: {e}")
            
            # Import UX results
            ux_results_dir = self.test_dir / "ux_results"
            if ux_results_dir.exists():
                for results_file in ux_results_dir.glob("ux_report_*.json"):
                    try:
                        self.success_monitor.import_test_results(results_file)
                    except Exception as e:
                        logger.warning(f"Failed to import {results_file}: {e}")
            
            # Generate monitoring report
            report = self.success_monitor.generate_monitoring_report(30)
            
            logger.info(f"✅ Monitoring analysis completed - Health Status: {report['health_status'].upper()}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Monitoring analysis failed: {e}")
            return {
                "error": str(e),
                "health_status": "unknown",
                "success_rates": {"overall": {"rate": 0.0}}
            }
    
    def run_comprehensive_test_suite(self, installer_dir: Optional[Path] = None) -> Dict:
        """Run the complete test suite"""
        logger.info("🚀 Starting comprehensive cross-platform installer testing")
        
        # Find installer files
        installer_files = self.find_installer_files(installer_dir)
        
        if not installer_files:
            logger.error("❌ No installer files found to test")
            self.test_session["summary"]["recommendations"].append(
                "No installer files found - ensure build process completed successfully"
            )
            return self.test_session
        
        # Run cross-platform tests
        if self.config["test_types"]["integrity"] or self.config["test_types"]["structure"] or self.config["test_types"]["installation"]:
            cross_platform_results = self.run_cross_platform_tests(installer_files)
            self.test_session["test_results"]["cross_platform"] = cross_platform_results
            
            # Update summary
            cp_summary = cross_platform_results.get("summary", {})
            self.test_session["summary"]["total_tests"] += cp_summary.get("total_tests", 0)
            self.test_session["summary"]["passed_tests"] += cp_summary.get("passed_tests", 0)
            self.test_session["summary"]["failed_tests"] += cp_summary.get("failed_tests", 0)
        
        # Run user experience tests
        if self.config["test_types"]["user_experience"]:
            ux_results = self.run_user_experience_tests(installer_files)
            self.test_session["test_results"]["user_experience"] = ux_results
            
            # Update summary with UX results
            ux_summary = ux_results.get("summary", {})
            ux_total = len(ux_results.get("user_tests", []))
            ux_successful = ux_summary.get("successful_installations", 0)
            
            self.test_session["summary"]["total_tests"] += ux_total
            self.test_session["summary"]["passed_tests"] += ux_successful
            self.test_session["summary"]["failed_tests"] += (ux_total - ux_successful)
        
        # Run monitoring analysis
        if self.config["test_types"]["monitoring"]:
            monitoring_results = self.run_monitoring_analysis()
            self.test_session["test_results"]["monitoring"] = monitoring_results
        
        # Calculate overall success rate
        total_tests = self.test_session["summary"]["total_tests"]
        if total_tests > 0:
            self.test_session["summary"]["overall_success_rate"] = (
                self.test_session["summary"]["passed_tests"] / total_tests * 100
            )
        
        # Generate recommendations
        self.generate_comprehensive_recommendations()
        
        # Finalize session
        self.test_session["end_time"] = datetime.now(timezone.utc).isoformat()
        
        # Save comprehensive report
        self.save_comprehensive_report()
        
        return self.test_session
    
    def generate_comprehensive_recommendations(self):
        """Generate comprehensive recommendations based on all test results"""
        recommendations = []
        
        # Cross-platform test recommendations
        cp_results = self.test_session["test_results"].get("cross_platform")
        if cp_results:
            cp_success_rate = cp_results.get("summary", {}).get("success_rate", 0)
            if cp_success_rate < 80:
                recommendations.append("CRITICAL: Cross-platform test success rate is below 80% - investigate installer integrity and structure issues")
            elif cp_success_rate < 90:
                recommendations.append("Improve cross-platform compatibility - some installers are failing basic tests")
        
        # User experience recommendations
        ux_results = self.test_session["test_results"].get("user_experience")
        if ux_results:
            satisfaction_score = ux_results.get("summary", {}).get("user_satisfaction_score", 0)
            if satisfaction_score < 6.0:
                recommendations.append("CRITICAL: User satisfaction score is below 6.0 - major UX improvements needed")
            elif satisfaction_score < 8.0:
                recommendations.append("Improve user experience - users are encountering significant pain points")
            
            # Add specific UX recommendations
            common_pain_points = ux_results.get("summary", {}).get("common_pain_points", [])
            for pain_point, count in common_pain_points[:3]:  # Top 3
                if "security warning" in pain_point.lower():
                    recommendations.append("Improve security warning documentation and user guidance")
                elif "too long" in pain_point.lower():
                    recommendations.append("Optimize installation and startup performance")
                elif "confusion" in pain_point.lower():
                    recommendations.append("Simplify user interface and improve clarity")
        
        # Monitoring recommendations
        monitoring_results = self.test_session["test_results"].get("monitoring")
        if monitoring_results:
            health_status = monitoring_results.get("health_status", "unknown")
            if health_status in ["critical", "poor"]:
                recommendations.append("URGENT: Installation success monitoring shows critical issues - immediate action required")
            elif health_status == "acceptable":
                recommendations.append("Installation success rate needs improvement - review failure patterns")
            
            # Add monitoring-specific recommendations
            monitoring_recommendations = monitoring_results.get("recommendations", [])
            recommendations.extend(monitoring_recommendations[:3])  # Top 3
        
        # Overall recommendations
        overall_success_rate = self.test_session["summary"]["overall_success_rate"]
        if overall_success_rate < 70:
            recommendations.append("CRITICAL: Overall test success rate is below 70% - do not release until major issues are resolved")
        elif overall_success_rate < 85:
            recommendations.append("Overall test success rate needs improvement before release")
        elif overall_success_rate >= 95:
            recommendations.append("Excellent test results - installers are ready for release")
        
        self.test_session["summary"]["recommendations"] = recommendations
    
    def save_comprehensive_report(self):
        """Save comprehensive test report"""
        # Save JSON report
        report_file = self.test_dir / f"comprehensive_test_report_{self.test_session['session_id']}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_session, f, indent=2)
        
        # Generate markdown report
        self.generate_comprehensive_markdown_report()
        
        logger.info(f"📄 Comprehensive test report saved: {report_file}")
    
    def generate_comprehensive_markdown_report(self):
        """Generate comprehensive markdown test report"""
        session = self.test_session
        summary = session["summary"]
        
        markdown_content = f"""# Comprehensive Cross-Platform Installer Test Report

## Test Session Information
- **Session ID**: {session['session_id']}
- **Platform**: {session['platform']}
- **Start Time**: {session['start_time']}
- **End Time**: {session.get('end_time', 'In Progress')}

## Overall Summary
- **Total Tests**: {summary['total_tests']}
- **Passed Tests**: {summary['passed_tests']} ✅
- **Failed Tests**: {summary['failed_tests']} ❌
- **Overall Success Rate**: {summary['overall_success_rate']:.1f}%

## Test Results by Category

### Cross-Platform Tests
"""
        
        cp_results = session["test_results"].get("cross_platform")
        if cp_results:
            cp_summary = cp_results.get("summary", {})
            markdown_content += f"""
- **Success Rate**: {cp_summary.get('success_rate', 0):.1f}%
- **Total Tests**: {cp_summary.get('total_tests', 0)}
- **Passed**: {cp_summary.get('passed_tests', 0)}
- **Failed**: {cp_summary.get('failed_tests', 0)}
"""
        else:
            markdown_content += "\n- **Status**: Not run or failed\n"
        
        markdown_content += "\n### User Experience Tests\n"
        
        ux_results = session["test_results"].get("user_experience")
        if ux_results:
            ux_summary = ux_results.get("summary", {})
            markdown_content += f"""
- **User Satisfaction Score**: {ux_summary.get('user_satisfaction_score', 0):.1f} / 10.0
- **Successful Installations**: {ux_summary.get('successful_installations', 0)}
- **Total User Personas**: {ux_summary.get('total_personas', 0)}
- **Average Installation Time**: {ux_summary.get('average_installation_time', 0):.1f} seconds
"""
        else:
            markdown_content += "\n- **Status**: Not run or failed\n"
        
        markdown_content += "\n### Installation Success Monitoring\n"
        
        monitoring_results = session["test_results"].get("monitoring")
        if monitoring_results:
            markdown_content += f"""
- **Health Status**: {monitoring_results.get('health_status', 'unknown').upper()}
- **Success Rate**: {monitoring_results.get('success_rates', {}).get('overall', {}).get('rate', 0):.1f}%
- **Active Alerts**: {len(monitoring_results.get('alerts', []))}
"""
        else:
            markdown_content += "\n- **Status**: Not run or failed\n"
        
        # Recommendations section
        markdown_content += f"""
## Recommendations

"""
        for recommendation in summary["recommendations"]:
            if "CRITICAL" in recommendation or "URGENT" in recommendation:
                markdown_content += f"- 🚨 {recommendation}\n"
            elif "WARNING" in recommendation.upper():
                markdown_content += f"- ⚠️ {recommendation}\n"
            else:
                markdown_content += f"- 💡 {recommendation}\n"
        
        # Overall assessment
        markdown_content += f"""
## Overall Assessment

"""
        
        overall_rate = summary["overall_success_rate"]
        if overall_rate >= 95:
            markdown_content += "🎉 **EXCELLENT**: All tests passed with flying colors. Installers are ready for release.\n"
        elif overall_rate >= 85:
            markdown_content += "✅ **GOOD**: Most tests passed successfully. Address minor issues before release.\n"
        elif overall_rate >= 70:
            markdown_content += "⚠️ **NEEDS IMPROVEMENT**: Several issues found. Address failed tests before release.\n"
        elif overall_rate >= 50:
            markdown_content += "❌ **POOR**: Major issues found. Significant work needed before release.\n"
        else:
            markdown_content += "🚨 **CRITICAL**: Severe issues found. Do not release until all critical issues are resolved.\n"
        
        # Release readiness
        markdown_content += f"""
## Release Readiness

"""
        
        if overall_rate >= 90:
            markdown_content += "✅ **READY FOR RELEASE**: All quality gates passed.\n"
        elif overall_rate >= 80:
            markdown_content += "⚠️ **CONDITIONAL RELEASE**: Address high-priority issues first.\n"
        else:
            markdown_content += "❌ **NOT READY FOR RELEASE**: Critical issues must be resolved.\n"
        
        # Save markdown report
        report_file = self.test_dir / f"comprehensive_test_report_{session['session_id']}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"📄 Comprehensive markdown report saved: {report_file}")

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Comprehensive cross-platform installer testing")
    parser.add_argument("--installer-dir", help="Directory containing installer files")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--skip-cross-platform", action="store_true", help="Skip cross-platform tests")
    parser.add_argument("--skip-user-experience", action="store_true", help="Skip user experience tests")
    parser.add_argument("--skip-monitoring", action="store_true", help="Skip monitoring analysis")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize test runner
    runner = CrossPlatformTestRunner(args.project_root)
    
    # Configure test types
    if args.skip_cross_platform:
        runner.config["test_types"]["integrity"] = False
        runner.config["test_types"]["structure"] = False
        runner.config["test_types"]["installation"] = False
    
    if args.skip_user_experience:
        runner.config["test_types"]["user_experience"] = False
    
    if args.skip_monitoring:
        runner.config["test_types"]["monitoring"] = False
    
    # Run comprehensive test suite
    installer_dir = Path(args.installer_dir) if args.installer_dir else None
    results = runner.run_comprehensive_test_suite(installer_dir)
    
    # Print summary
    summary = results["summary"]
    logger.info(f"🎯 Comprehensive Testing Complete:")
    logger.info(f"   Overall Success Rate: {summary['overall_success_rate']:.1f}%")
    logger.info(f"   Total Tests: {summary['total_tests']}")
    logger.info(f"   Passed: {summary['passed_tests']}")
    logger.info(f"   Failed: {summary['failed_tests']}")
    logger.info(f"   Recommendations: {len(summary['recommendations'])}")
    
    # Exit with appropriate code
    success = summary["overall_success_rate"] >= 80.0
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()