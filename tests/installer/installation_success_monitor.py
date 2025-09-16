#!/usr/bin/env python3
"""
Installation Success Rate Monitoring and Reporting System
Tracks and analyzes installation success rates across platforms and versions
"""

import os
import sys
import json
import time
import platform
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import statistics
try:
    import requests
except ImportError:
    requests = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InstallationSuccessMonitor:
    """Monitors and tracks installation success rates with detailed analytics"""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.monitoring_dir = self.project_root / "tests" / "installer" / "monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.monitoring_dir / "installation_success.db"
        self.init_database()
        
        # Configuration
        self.config = {
            "success_rate_thresholds": {
                "excellent": 95.0,
                "good": 85.0,
                "acceptable": 75.0,
                "poor": 60.0
            },
            "monitoring_window_days": 30,
            "alert_thresholds": {
                "critical_failure_rate": 40.0,  # Alert if failure rate > 40%
                "significant_drop": 10.0,       # Alert if success rate drops > 10%
                "minimum_samples": 10            # Minimum tests before alerting
            }
        }
    
    def init_database(self):
        """Initialize SQLite database for tracking installation results"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS installation_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    platform_version TEXT,
                    installer_file TEXT NOT NULL,
                    installer_version TEXT,
                    installer_type TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    duration_seconds REAL,
                    error_message TEXT,
                    user_persona TEXT,
                    technical_level TEXT,
                    test_details TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS success_rate_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    installer_type TEXT NOT NULL,
                    time_window_days INTEGER NOT NULL,
                    total_tests INTEGER NOT NULL,
                    successful_tests INTEGER NOT NULL,
                    success_rate REAL NOT NULL,
                    average_duration REAL,
                    common_errors TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    platform TEXT,
                    installer_type TEXT,
                    message TEXT NOT NULL,
                    details TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON installation_tests(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform ON installation_tests(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_success ON installation_tests(success)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_installer_type ON installation_tests(installer_type)')
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def record_installation_test(self, test_result: Dict):
        """Record an installation test result in the database"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO installation_tests (
                    timestamp, session_id, platform, platform_version,
                    installer_file, installer_version, installer_type,
                    test_type, success, duration_seconds, error_message,
                    user_persona, technical_level, test_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_result.get('timestamp', datetime.now(timezone.utc).isoformat()),
                test_result.get('session_id', ''),
                test_result.get('platform', platform.system().lower()),
                test_result.get('platform_version', platform.release()),
                test_result.get('installer_file', ''),
                test_result.get('installer_version', ''),
                test_result.get('installer_type', ''),
                test_result.get('test_type', 'automated'),
                test_result.get('success', False),
                test_result.get('duration_seconds', 0.0),
                test_result.get('error_message', ''),
                test_result.get('user_persona', ''),
                test_result.get('technical_level', ''),
                json.dumps(test_result.get('details', {}))
            ))
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def import_test_results(self, test_results_file: Path):
        """Import test results from JSON file"""
        logger.info(f"📥 Importing test results from {test_results_file}")
        
        try:
            with open(test_results_file, 'r') as f:
                data = json.load(f)
            
            # Handle different test result formats
            if 'tests' in data:  # Cross-platform test results
                for test in data['tests']:
                    test_result = {
                        'timestamp': data.get('start_time', datetime.now(timezone.utc).isoformat()),
                        'session_id': data.get('session_id', ''),
                        'platform': data.get('platform', ''),
                        'test_type': 'automated',
                        'success': test.get('status') == 'passed',
                        'duration_seconds': test.get('duration_seconds', 0.0),
                        'error_message': str(test.get('details', {}).get('error', '')),
                        'installer_file': test.get('test_name', '').split('_')[-1] if '_' in test.get('test_name', '') else '',
                        'installer_type': self.detect_installer_type(test.get('test_name', '')),
                        'details': test.get('details', {})
                    }
                    self.record_installation_test(test_result)
            
            elif 'user_tests' in data:  # UX test results
                for test in data['user_tests']:
                    test_result = {
                        'timestamp': test.get('start_time', datetime.now(timezone.utc).isoformat()),
                        'session_id': data.get('session_id', ''),
                        'platform': data.get('platform', ''),
                        'test_type': 'user_experience',
                        'success': test.get('success', False),
                        'duration_seconds': test.get('total_time_seconds', 0.0),
                        'user_persona': test.get('persona', ''),
                        'technical_level': test.get('technical_level', ''),
                        'installer_file': test.get('installer_file', ''),
                        'installer_type': self.detect_installer_type(test.get('installer_file', '')),
                        'details': {
                            'satisfaction_score': test.get('satisfaction_score', 0),
                            'pain_points': test.get('pain_points', []),
                            'positive_points': test.get('positive_points', [])
                        }
                    }
                    self.record_installation_test(test_result)
            
            logger.info("✅ Test results imported successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to import test results: {e}")
    
    def detect_installer_type(self, filename: str) -> str:
        """Detect installer type from filename"""
        filename_lower = filename.lower()
        if '.exe' in filename_lower:
            return 'windows_exe'
        elif '.dmg' in filename_lower:
            return 'macos_dmg'
        elif '.deb' in filename_lower:
            return 'linux_deb'
        elif '.rpm' in filename_lower:
            return 'linux_rpm'
        elif '.appimage' in filename_lower:
            return 'linux_appimage'
        elif '.tar.gz' in filename_lower:
            return 'linux_tarball'
        else:
            return 'unknown'
    
    def calculate_success_rates(self, days: int = 30) -> Dict:
        """Calculate success rates for the specified time window"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall success rate
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM installation_tests
                WHERE timestamp >= ?
            ''', (cutoff_date,))
            
            result = cursor.fetchone()
            total, successful = result if result else (0, 0)
            successful = successful or 0  # Handle None case
            overall_rate = (successful / total * 100) if total > 0 else 0
            
            # Success rate by platform
            cursor.execute('''
                SELECT platform, COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM installation_tests
                WHERE timestamp >= ?
                GROUP BY platform
            ''', (cutoff_date,))
            
            platform_rates = {}
            for platform_name, total, successful in cursor.fetchall():
                successful = successful or 0  # Handle None case
                platform_rates[platform_name] = {
                    'total': total,
                    'successful': successful,
                    'rate': (successful / total * 100) if total > 0 else 0
                }
            
            # Success rate by installer type
            cursor.execute('''
                SELECT installer_type, COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM installation_tests
                WHERE timestamp >= ?
                GROUP BY installer_type
            ''', (cutoff_date,))
            
            installer_rates = {}
            for installer_type, total, successful in cursor.fetchall():
                successful = successful or 0  # Handle None case
                installer_rates[installer_type] = {
                    'total': total,
                    'successful': successful,
                    'rate': (successful / total * 100) if total > 0 else 0
                }
            
            # Success rate by user persona (for UX tests)
            cursor.execute('''
                SELECT user_persona, COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM installation_tests
                WHERE timestamp >= ? AND user_persona != ''
                GROUP BY user_persona
            ''', (cutoff_date,))
            
            persona_rates = {}
            for persona, total, successful in cursor.fetchall():
                successful = successful or 0  # Handle None case
                persona_rates[persona] = {
                    'total': total,
                    'successful': successful,
                    'rate': (successful / total * 100) if total > 0 else 0
                }
            
            return {
                'time_window_days': days,
                'overall': {
                    'total': total,
                    'successful': successful,
                    'rate': overall_rate
                },
                'by_platform': platform_rates,
                'by_installer_type': installer_rates,
                'by_user_persona': persona_rates
            }
        finally:
            if conn:
                conn.close()
    
    def get_failure_analysis(self, days: int = 30) -> Dict:
        """Analyze failure patterns and common issues"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Common error messages
            cursor.execute('''
                SELECT error_message, COUNT(*) as count
                FROM installation_tests
                WHERE timestamp >= ? AND success = FALSE AND error_message != ''
                GROUP BY error_message
                ORDER BY count DESC
                LIMIT 10
            ''', (cutoff_date,))
            
            common_errors = [{'error': error, 'count': count} for error, count in cursor.fetchall()]
            
            # Failure rate by platform
            cursor.execute('''
                SELECT platform, COUNT(*) as total, SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as failures
                FROM installation_tests
                WHERE timestamp >= ?
                GROUP BY platform
            ''', (cutoff_date,))
            
            platform_failures = {}
            for platform_name, total, failures in cursor.fetchall():
                platform_failures[platform_name] = {
                    'total': total,
                    'failures': failures,
                    'failure_rate': (failures / total * 100) if total > 0 else 0
                }
            
            # Average duration for failed vs successful tests
            cursor.execute('''
                SELECT success, AVG(duration_seconds) as avg_duration
                FROM installation_tests
                WHERE timestamp >= ? AND duration_seconds > 0
                GROUP BY success
            ''', (cutoff_date,))
            
            duration_analysis = {}
            for success, avg_duration in cursor.fetchall():
                duration_analysis['successful' if success else 'failed'] = avg_duration
            
            return {
                'common_errors': common_errors,
                'platform_failures': platform_failures,
                'duration_analysis': duration_analysis
            }
    
    def detect_trends(self, days: int = 30) -> Dict:
        """Detect trends in success rates over time"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Daily success rates for trend analysis
            cursor.execute('''
                SELECT DATE(timestamp) as date, 
                       COUNT(*) as total, 
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM installation_tests
                WHERE timestamp >= DATE('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            '''.format(days))
            
            daily_rates = []
            for date, total, successful in cursor.fetchall():
                rate = (successful / total * 100) if total > 0 else 0
                daily_rates.append({
                    'date': date,
                    'total': total,
                    'successful': successful,
                    'rate': rate
                })
            
            # Calculate trend
            if len(daily_rates) >= 7:  # Need at least a week of data
                rates = [day['rate'] for day in daily_rates]
                
                # Simple linear trend calculation
                x = list(range(len(rates)))
                n = len(rates)
                sum_x = sum(x)
                sum_y = sum(rates)
                sum_xy = sum(x[i] * rates[i] for i in range(n))
                sum_x2 = sum(x[i] ** 2 for i in range(n))
                
                if n * sum_x2 - sum_x ** 2 != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                    trend = 'improving' if slope > 0.5 else 'declining' if slope < -0.5 else 'stable'
                else:
                    trend = 'stable'
                    slope = 0
            else:
                trend = 'insufficient_data'
                slope = 0
            
            return {
                'daily_rates': daily_rates,
                'trend': trend,
                'slope': slope,
                'data_points': len(daily_rates)
            }
    
    def check_alerts(self) -> List[Dict]:
        """Check for conditions that should trigger alerts"""
        alerts = []
        
        # Get recent success rates
        recent_rates = self.calculate_success_rates(7)  # Last 7 days
        overall_rate = recent_rates['overall']['rate']
        total_tests = recent_rates['overall']['total']
        
        # Check if we have enough data
        if total_tests < self.config['alert_thresholds']['minimum_samples']:
            return alerts
        
        # Critical failure rate alert
        if overall_rate < (100 - self.config['alert_thresholds']['critical_failure_rate']):
            alerts.append({
                'type': 'critical_failure_rate',
                'severity': 'critical',
                'message': f'Critical: Overall success rate is only {overall_rate:.1f}%',
                'details': {
                    'success_rate': overall_rate,
                    'total_tests': total_tests,
                    'threshold': 100 - self.config['alert_thresholds']['critical_failure_rate']
                }
            })
        
        # Check for significant drops
        older_rates = self.calculate_success_rates(30)  # Last 30 days
        if older_rates['overall']['total'] >= self.config['alert_thresholds']['minimum_samples']:
            rate_drop = older_rates['overall']['rate'] - overall_rate
            if rate_drop > self.config['alert_thresholds']['significant_drop']:
                alerts.append({
                    'type': 'significant_drop',
                    'severity': 'warning',
                    'message': f'Warning: Success rate dropped by {rate_drop:.1f}% in recent tests',
                    'details': {
                        'recent_rate': overall_rate,
                        'historical_rate': older_rates['overall']['rate'],
                        'drop': rate_drop
                    }
                })
        
        # Platform-specific alerts
        for platform, data in recent_rates['by_platform'].items():
            if data['total'] >= 5 and data['rate'] < 50:  # Platform-specific critical threshold
                alerts.append({
                    'type': 'platform_failure',
                    'severity': 'critical',
                    'platform': platform,
                    'message': f'Critical: {platform} success rate is only {data["rate"]:.1f}%',
                    'details': data
                })
        
        # Record alerts in database
        for alert in alerts:
            self.record_alert(alert)
        
        return alerts
    
    def cleanup(self):
        """Clean up database connections"""
        # Force close any lingering connections
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
        except:
            pass
    
    def record_alert(self, alert: Dict):
        """Record an alert in the database"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (
                    timestamp, alert_type, severity, platform,
                    installer_type, message, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc).isoformat(),
                alert.get('type', ''),
                alert.get('severity', ''),
                alert.get('platform', ''),
                alert.get('installer_type', ''),
                alert.get('message', ''),
                json.dumps(alert.get('details', {}))
            ))
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def generate_monitoring_report(self, days: int = 30) -> Dict:
        """Generate comprehensive monitoring report"""
        logger.info(f"📊 Generating monitoring report for last {days} days")
        
        # Calculate success rates
        success_rates = self.calculate_success_rates(days)
        
        # Get failure analysis
        failure_analysis = self.get_failure_analysis(days)
        
        # Detect trends
        trends = self.detect_trends(days)
        
        # Check for alerts
        alerts = self.check_alerts()
        
        # Determine overall health status
        overall_rate = success_rates['overall']['rate']
        if overall_rate >= self.config['success_rate_thresholds']['excellent']:
            health_status = 'excellent'
        elif overall_rate >= self.config['success_rate_thresholds']['good']:
            health_status = 'good'
        elif overall_rate >= self.config['success_rate_thresholds']['acceptable']:
            health_status = 'acceptable'
        elif overall_rate >= self.config['success_rate_thresholds']['poor']:
            health_status = 'poor'
        else:
            health_status = 'critical'
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'time_window_days': days,
            'health_status': health_status,
            'success_rates': success_rates,
            'failure_analysis': failure_analysis,
            'trends': trends,
            'alerts': alerts,
            'recommendations': self.generate_recommendations(success_rates, failure_analysis, trends)
        }
        
        # Save report
        report_file = self.monitoring_dir / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self.generate_monitoring_markdown_report(report)
        
        logger.info(f"📄 Monitoring report saved: {report_file}")
        return report
    
    def generate_recommendations(self, success_rates: Dict, failure_analysis: Dict, trends: Dict) -> List[str]:
        """Generate actionable recommendations based on monitoring data"""
        recommendations = []
        
        overall_rate = success_rates['overall']['rate']
        
        # Overall success rate recommendations
        if overall_rate < 75:
            recommendations.append("URGENT: Overall success rate is below acceptable threshold. Investigate and fix critical issues immediately.")
        elif overall_rate < 85:
            recommendations.append("Improve overall success rate by addressing common failure patterns.")
        
        # Platform-specific recommendations
        for platform, data in success_rates['by_platform'].items():
            if data['rate'] < 70:
                recommendations.append(f"Focus on {platform} platform - success rate is critically low at {data['rate']:.1f}%")
            elif data['rate'] < overall_rate - 10:
                recommendations.append(f"Investigate {platform} platform issues - performing below average")
        
        # Installer type recommendations
        for installer_type, data in success_rates['by_installer_type'].items():
            if data['rate'] < 70:
                recommendations.append(f"Review {installer_type} installer - success rate is {data['rate']:.1f}%")
        
        # Common error recommendations
        if failure_analysis['common_errors']:
            top_error = failure_analysis['common_errors'][0]
            recommendations.append(f"Address most common error: '{top_error['error']}' (affects {top_error['count']} installations)")
        
        # Trend-based recommendations
        if trends['trend'] == 'declining':
            recommendations.append("Success rate is declining - investigate recent changes and implement fixes")
        elif trends['trend'] == 'improving':
            recommendations.append("Success rate is improving - continue current improvement efforts")
        
        # Duration-based recommendations
        duration_analysis = failure_analysis.get('duration_analysis', {})
        if 'failed' in duration_analysis and 'successful' in duration_analysis:
            if duration_analysis['failed'] > duration_analysis['successful'] * 2:
                recommendations.append("Failed installations take significantly longer - improve error handling and timeouts")
        
        return recommendations
    
    def generate_monitoring_markdown_report(self, report: Dict):
        """Generate markdown monitoring report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        markdown_content = f"""# Installation Success Rate Monitoring Report

## Report Information
- **Generated**: {report['timestamp']}
- **Time Window**: {report['time_window_days']} days
- **Health Status**: {report['health_status'].upper()}

## Overall Success Rate
- **Success Rate**: {report['success_rates']['overall']['rate']:.1f}%
- **Total Tests**: {report['success_rates']['overall']['total']}
- **Successful**: {report['success_rates']['overall']['successful']}

## Success Rate by Platform

| Platform | Success Rate | Total Tests | Successful |
|----------|--------------|-------------|------------|
"""
        
        for platform, data in report['success_rates']['by_platform'].items():
            markdown_content += f"| {platform} | {data['rate']:.1f}% | {data['total']} | {data['successful']} |\n"
        
        markdown_content += f"""
## Success Rate by Installer Type

| Installer Type | Success Rate | Total Tests | Successful |
|----------------|--------------|-------------|------------|
"""
        
        for installer_type, data in report['success_rates']['by_installer_type'].items():
            markdown_content += f"| {installer_type} | {data['rate']:.1f}% | {data['total']} | {data['successful']} |\n"
        
        # Trends section
        trends = report['trends']
        markdown_content += f"""
## Trends Analysis
- **Trend**: {trends['trend'].replace('_', ' ').title()}
- **Data Points**: {trends['data_points']} days
- **Slope**: {trends['slope']:.2f}
"""
        
        # Alerts section
        if report['alerts']:
            markdown_content += f"""
## Active Alerts

"""
            for alert in report['alerts']:
                severity_icon = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(alert['severity'], '❓')
                markdown_content += f"- {severity_icon} **{alert['severity'].upper()}**: {alert['message']}\n"
        else:
            markdown_content += "\n## Active Alerts\n\n✅ No active alerts\n"
        
        # Common errors section
        if report['failure_analysis']['common_errors']:
            markdown_content += f"""
## Most Common Errors

"""
            for error in report['failure_analysis']['common_errors'][:5]:
                markdown_content += f"- **{error['error']}**: {error['count']} occurrences\n"
        
        # Recommendations section
        markdown_content += f"""
## Recommendations

"""
        for recommendation in report['recommendations']:
            markdown_content += f"- {recommendation}\n"
        
        # Health status interpretation
        markdown_content += f"""
## Health Status Interpretation

"""
        health_status = report['health_status']
        if health_status == 'excellent':
            markdown_content += "🎉 **Excellent**: Installation success rate is outstanding. Continue current practices.\n"
        elif health_status == 'good':
            markdown_content += "✅ **Good**: Installation success rate is good with room for minor improvements.\n"
        elif health_status == 'acceptable':
            markdown_content += "⚠️ **Acceptable**: Installation success rate meets minimum standards but needs improvement.\n"
        elif health_status == 'poor':
            markdown_content += "❌ **Poor**: Installation success rate is below acceptable standards. Immediate action required.\n"
        else:
            markdown_content += "🚨 **Critical**: Installation success rate is critically low. Emergency action required.\n"
        
        # Save markdown report
        report_file = self.monitoring_dir / f"monitoring_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"📄 Monitoring markdown report saved: {report_file}")

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Installation success rate monitoring")
    parser.add_argument("--import-results", help="Import test results from JSON file")
    parser.add_argument("--generate-report", action="store_true", help="Generate monitoring report")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--check-alerts", action="store_true", help="Check for alerts only")
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = InstallationSuccessMonitor(args.project_root)
    
    if args.import_results:
        results_file = Path(args.import_results)
        if results_file.exists():
            monitor.import_test_results(results_file)
        else:
            logger.error(f"Results file not found: {results_file}")
            sys.exit(1)
    
    if args.check_alerts:
        alerts = monitor.check_alerts()
        if alerts:
            logger.warning(f"⚠️ {len(alerts)} alerts found:")
            for alert in alerts:
                logger.warning(f"  - {alert['severity'].upper()}: {alert['message']}")
            sys.exit(1)
        else:
            logger.info("✅ No alerts")
    
    if args.generate_report:
        report = monitor.generate_monitoring_report(args.days)
        
        # Print summary
        logger.info(f"📊 Monitoring Report Summary:")
        logger.info(f"   Health Status: {report['health_status'].upper()}")
        logger.info(f"   Success Rate: {report['success_rates']['overall']['rate']:.1f}%")
        logger.info(f"   Total Tests: {report['success_rates']['overall']['total']}")
        logger.info(f"   Active Alerts: {len(report['alerts'])}")
        
        # Exit with appropriate code
        success = report['health_status'] in ['excellent', 'good', 'acceptable']
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()