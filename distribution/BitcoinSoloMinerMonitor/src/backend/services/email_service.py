"""
Email Service

This module provides email notification functionality for the Bitcoin Solo Miner Monitoring App.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from jinja2 import Environment, BaseLoader
from email_validator import validate_email, EmailNotValidError

from config.app_config import EMAIL_CONFIG

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending email notifications.
    """
    
    def __init__(self):
        """Initialize the email service."""
        self.config = EMAIL_CONFIG.copy()
        self.rate_limit_tracker = {
            "hourly": {},
            "daily": {}
        }
        self.jinja_env = Environment(loader=BaseLoader())
        
    async def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return (
            self.config.get("enabled", False) and
            bool(self.config.get("smtp_server")) and
            bool(self.config.get("username")) and
            bool(self.config.get("password")) and
            bool(self.config.get("from_address"))
        )
    
    async def validate_email_address(self, email: str) -> Dict[str, Any]:
        """
        Validate an email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Dict with validation result
        """
        try:
            # Normalize and validate the email
            valid = validate_email(email)
            return {
                "valid": True,
                "email": valid.email,
                "normalized": valid.email
            }
        except EmailNotValidError as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update email configuration.
        
        Args:
            new_config: New configuration settings
            
        Returns:
            Updated configuration
        """
        # Validate required fields if enabling
        if new_config.get("enabled", False):
            required_fields = ["smtp_server", "username", "password", "from_address"]
            missing_fields = [field for field in required_fields if not new_config.get(field)]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Update configuration
        self.config.update(new_config)
        
        return self.config
    
    async def get_config(self) -> Dict[str, Any]:
        """
        Get current email configuration (without sensitive data).
        
        Returns:
            Configuration without passwords
        """
        safe_config = self.config.copy()
        # Remove sensitive information
        if "password" in safe_config:
            safe_config["password"] = "***" if safe_config["password"] else ""
        
        return safe_config
    
    def _check_rate_limit(self, email: str) -> bool:
        """
        Check if email sending is within rate limits.
        
        Args:
            email: Recipient email address
            
        Returns:
            True if within limits, False otherwise
        """
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")
        
        # Clean old entries
        self._clean_rate_limit_tracker()
        
        # Check hourly limit
        hourly_count = self.rate_limit_tracker["hourly"].get(hour_key, {}).get(email, 0)
        if hourly_count >= self.config["rate_limit"]["max_emails_per_hour"]:
            return False
        
        # Check daily limit
        daily_count = self.rate_limit_tracker["daily"].get(day_key, {}).get(email, 0)
        if daily_count >= self.config["rate_limit"]["max_emails_per_day"]:
            return False
        
        return True
    
    def _update_rate_limit(self, email: str):
        """
        Update rate limit counters for an email.
        
        Args:
            email: Recipient email address
        """
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")
        
        # Update hourly counter
        if hour_key not in self.rate_limit_tracker["hourly"]:
            self.rate_limit_tracker["hourly"][hour_key] = {}
        self.rate_limit_tracker["hourly"][hour_key][email] = (
            self.rate_limit_tracker["hourly"][hour_key].get(email, 0) + 1
        )
        
        # Update daily counter
        if day_key not in self.rate_limit_tracker["daily"]:
            self.rate_limit_tracker["daily"][day_key] = {}
        self.rate_limit_tracker["daily"][day_key][email] = (
            self.rate_limit_tracker["daily"][day_key].get(email, 0) + 1
        )
    
    def _clean_rate_limit_tracker(self):
        """Clean old entries from rate limit tracker."""
        now = datetime.now()
        
        # Clean hourly entries older than 24 hours
        cutoff_hour = (now - timedelta(hours=24)).strftime("%Y-%m-%d-%H")
        self.rate_limit_tracker["hourly"] = {
            k: v for k, v in self.rate_limit_tracker["hourly"].items()
            if k >= cutoff_hour
        }
        
        # Clean daily entries older than 30 days
        cutoff_day = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        self.rate_limit_tracker["daily"] = {
            k: v for k, v in self.rate_limit_tracker["daily"].items()
            if k >= cutoff_day
        }
    
    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        
        Args:
            to_email: Recipient email address
            
        Returns:
            Result of the test
        """
        if not await self.is_configured():
            return {
                "success": False,
                "error": "Email service is not configured"
            }
        
        # Validate email address
        validation = await self.validate_email_address(to_email)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid email address: {validation['error']}"
            }
        
        # Check rate limits
        if not self._check_rate_limit(to_email):
            return {
                "success": False,
                "error": "Rate limit exceeded"
            }
        
        try:
            # Create test email using unified template
            subject = "✅ Bitcoin Miner Monitor - Test Email"
            
            # Test email configuration
            test_config = {
                "icon": "✅",
                "title": "Email Configuration Test",
                "priority": "info",
                "color": "#28a745",
                "message": "This is a test email to verify your email notification settings are working correctly.",
                "action": "If you received this email, your configuration is working perfectly! You can now receive mining alerts via email.",
                "details": [
                    {"label": "Test Type", "value": "SMTP Configuration"},
                    {"label": "Status", "value": "Successful"},
                    {"label": "Recipient", "value": to_email},
                    {"label": "Service", "value": "Email Notifications"}
                ]
            }
            
            # Prepare template data
            template_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "notification_type": "test_email",
                "config": test_config
            }
            
            # Generate body using unified template
            body = self._render_unified_template(test_config, template_data)
            
            result = await self._send_email(to_email, subject, body)
            
            if result["success"]:
                self._update_rate_limit(to_email)
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return {
                "success": False,
                "error": f"Failed to send test email: {str(e)}"
            }
    
    async def send_notification_email(
        self, 
        to_email: str, 
        notification_type: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a notification email.
        
        Args:
            to_email: Recipient email address
            notification_type: Type of notification (miner_offline, temperature_alert, etc.)
            data: Notification data
            
        Returns:
            Result of sending the email
        """
        if not await self.is_configured():
            return {
                "success": False,
                "error": "Email service is not configured"
            }
        
        # Validate email address
        validation = await self.validate_email_address(to_email)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid email address: {validation['error']}"
            }
        
        # Check rate limits
        if not self._check_rate_limit(to_email):
            return {
                "success": False,
                "error": "Rate limit exceeded"
            }
        
        try:
            # Generate email content based on notification type
            subject, body = self._generate_notification_content(notification_type, data)
            
            result = await self._send_email(to_email, subject, body)
            
            if result["success"]:
                self._update_rate_limit(to_email)
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending notification email: {e}")
            return {
                "success": False,
                "error": f"Failed to send notification email: {str(e)}"
            }
    
    def _generate_notification_content(self, notification_type: str, data: Dict[str, Any]) -> tuple:
        """
        Generate email subject and body for a notification using a unified template.
        
        Args:
            notification_type: Type of notification
            data: Notification data
            
        Returns:
            Tuple of (subject, body)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Define notification configurations
        notification_configs = {
            "miner_offline": {
                "subject": "🚨 Miner Offline Alert - {{miner_name}}",
                "icon": "🚨",
                "title": "Miner Offline Alert",
                "priority": "critical",
                "color": "#dc3545",
                "message": "Your miner has gone offline and is no longer responding to status requests.",
                "action": "Please check your miner's power and network connection.",
                "details": [
                    {"label": "Miner", "value": "{{miner_name}} ({{miner_ip}})"},
                    {"label": "Status", "value": "Offline"},
                    {"label": "Last Seen", "value": "{{last_seen|default('Unknown')}}"}
                ]
            },
            "temperature_alert": {
                "subject": "🌡️ Temperature Alert - {{miner_name}}",
                "icon": "🌡️",
                "title": "High Temperature Alert",
                "priority": "warning",
                "color": "#fd7e14",
                "message": "Your miner is running at a high temperature that may affect performance and longevity.",
                "action": "Please check ventilation and cooling systems immediately.",
                "details": [
                    {"label": "Miner", "value": "{{miner_name}} ({{miner_ip}})"},
                    {"label": "Current Temperature", "value": "{{temperature}}°C"},
                    {"label": "Threshold", "value": "{{threshold}}°C"},
                    {"label": "Severity", "value": "{{severity|default('High')}}"}
                ]
            },
            "hashrate_drop": {
                "subject": "📉 Hashrate Drop Alert - {{miner_name}}",
                "icon": "📉",
                "title": "Hashrate Drop Alert",
                "priority": "warning",
                "color": "#ffc107",
                "message": "Your miner's hashrate has dropped significantly below expected performance.",
                "action": "Please check for hardware issues, network connectivity, or pool problems.",
                "details": [
                    {"label": "Miner", "value": "{{miner_name}} ({{miner_ip}})"},
                    {"label": "Current Hashrate", "value": "{{current_hashrate}}"},
                    {"label": "Expected Hashrate", "value": "{{expected_hashrate}}"},
                    {"label": "Drop Percentage", "value": "{{drop_percentage}}%"}
                ]
            },
            "new_miner": {
                "subject": "🔍 New Miner Discovered - {{miner_name}}",
                "icon": "🔍",
                "title": "New Miner Discovered",
                "priority": "info",
                "color": "#17a2b8",
                "message": "A new miner has been discovered on your network and automatically added to monitoring.",
                "action": "Review the miner settings and configure alerts as needed.",
                "details": [
                    {"label": "Miner", "value": "{{miner_name}} ({{miner_ip}})"},
                    {"label": "Type", "value": "{{miner_type}}"},
                    {"label": "Model", "value": "{{model|default('Unknown')}}"},
                    {"label": "Status", "value": "{{status|default('Active')}}"}
                ]
            }
        }
        
        # Get configuration for notification type
        config = notification_configs.get(notification_type, {
            "subject": "Bitcoin Miner Monitor Notification",
            "icon": "📢",
            "title": "System Notification",
            "priority": "info",
            "color": "#6c757d",
            "message": "A system notification has been generated.",
            "action": "Please check your mining dashboard for more details.",
            "details": [
                {"label": "Type", "value": "{{notification_type}}"},
                {"label": "Data", "value": "{{data}}"}
            ]
        })
        
        # Prepare template data
        template_data = data.copy()
        template_data.update({
            "timestamp": timestamp,
            "notification_type": notification_type,
            "data": str(data),
            "config": config
        })
        
        # Generate subject
        subject_template = self.jinja_env.from_string(config["subject"])
        subject = subject_template.render(**template_data)
        
        # Generate body using unified template
        body = self._render_unified_template(config, template_data)
        
        return subject, body
    
    def _render_unified_template(self, config: Dict[str, Any], data: Dict[str, Any]) -> str:
        """
        Render the unified email template with proper branding and styling.
        
        Args:
            config: Notification configuration
            data: Template data
            
        Returns:
            Rendered HTML email body
        """
        # Create Jinja environment with the template data
        template_data = data.copy()
        template_data["config"] = config
        
        # Unified HTML email template
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{config.title}} - Bitcoin Miner Monitor</title>
    <style>
        /* Reset styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        /* Base styles */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333333;
            background-color: #f8f9fa;
            margin: 0;
            padding: 20px;
        }
        
        /* Container */
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        /* Header */
        .email-header {
            background: linear-gradient(135deg, #f7931a 0%, #ff9500 100%);
            color: white;
            padding: 30px 40px;
            text-align: center;
        }
        
        .logo-section {
            margin-bottom: 20px;
        }
        
        .logo-icon {
            font-size: 48px;
            margin-bottom: 10px;
            display: block;
        }
        
        .app-name {
            font-size: 24px;
            font-weight: 700;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        .app-tagline {
            font-size: 14px;
            opacity: 0.9;
            margin: 5px 0 0 0;
        }
        
        /* Alert section */
        .alert-section {
            padding: 40px;
            text-align: center;
        }
        
        .alert-icon {
            font-size: 64px;
            margin-bottom: 20px;
            display: block;
        }
        
        .alert-title {
            font-size: 28px;
            font-weight: 700;
            color: {{config.color}};
            margin-bottom: 15px;
        }
        
        .alert-message {
            font-size: 16px;
            color: #555555;
            margin-bottom: 25px;
            line-height: 1.7;
        }
        
        .priority-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 30px;
        }
        
        .priority-critical {
            background-color: #dc3545;
            color: white;
        }
        
        .priority-warning {
            background-color: #fd7e14;
            color: white;
        }
        
        .priority-info {
            background-color: #17a2b8;
            color: white;
        }
        
        /* Details section */
        .details-section {
            background-color: #f8f9fa;
            padding: 30px 40px;
            border-top: 1px solid #e9ecef;
        }
        
        .details-title {
            font-size: 18px;
            font-weight: 600;
            color: #333333;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .details-grid {
            display: table;
            width: 100%;
            border-collapse: collapse;
        }
        
        .detail-row {
            display: table-row;
        }
        
        .detail-label {
            display: table-cell;
            padding: 12px 20px 12px 0;
            font-weight: 600;
            color: #555555;
            border-bottom: 1px solid #e9ecef;
            width: 40%;
        }
        
        .detail-value {
            display: table-cell;
            padding: 12px 0;
            color: #333333;
            border-bottom: 1px solid #e9ecef;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
        }
        
        /* Action section */
        .action-section {
            padding: 30px 40px;
            background-color: #ffffff;
            border-top: 1px solid #e9ecef;
        }
        
        .action-title {
            font-size: 16px;
            font-weight: 600;
            color: #333333;
            margin-bottom: 15px;
        }
        
        .action-message {
            font-size: 14px;
            color: #666666;
            line-height: 1.6;
            margin-bottom: 25px;
        }
        
        .action-button {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #f7931a 0%, #ff9500 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(247, 147, 26, 0.3);
            transition: all 0.3s ease;
        }
        
        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(247, 147, 26, 0.4);
        }
        
        /* Footer */
        .email-footer {
            background-color: #343a40;
            color: #ffffff;
            padding: 25px 40px;
            text-align: center;
            font-size: 12px;
        }
        
        .footer-text {
            margin-bottom: 10px;
            opacity: 0.8;
        }
        
        .footer-links {
            margin-top: 15px;
        }
        
        .footer-link {
            color: #f7931a;
            text-decoration: none;
            margin: 0 10px;
        }
        
        .footer-link:hover {
            text-decoration: underline;
        }
        
        /* Responsive design */
        @media only screen and (max-width: 600px) {
            body { padding: 10px; }
            .email-header, .alert-section, .details-section, .action-section, .email-footer {
                padding: 20px;
            }
            .alert-title { font-size: 24px; }
            .alert-icon { font-size: 48px; }
            .detail-label, .detail-value { 
                display: block; 
                width: 100%; 
                padding: 8px 0;
            }
            .detail-label { font-weight: 600; }
        }
    </style>
</head>
<body>
    <div class="email-container">
        <!-- Header -->
        <div class="email-header">
            <div class="logo-section">
                <span class="logo-icon">₿</span>
                <h1 class="app-name">Bitcoin Miner Monitor</h1>
                <p class="app-tagline">Professional Mining Operations Management</p>
            </div>
        </div>
        
        <!-- Alert Section -->
        <div class="alert-section">
            <span class="alert-icon">{{config.icon}}</span>
            <h2 class="alert-title">{{config.title}}</h2>
            <div class="priority-badge priority-{{config.priority}}">{{config.priority}} Priority</div>
            <p class="alert-message">{{config.message}}</p>
        </div>
        
        <!-- Details Section -->
        <div class="details-section">
            <h3 class="details-title">Alert Details</h3>
            <div class="details-grid">
                {% for detail in config.details %}
                <div class="detail-row">
                    <div class="detail-label">{{detail.label}}:</div>
                    <div class="detail-value">{{detail.value}}</div>
                </div>
                {% endfor %}
                <div class="detail-row">
                    <div class="detail-label">Timestamp:</div>
                    <div class="detail-value">{{timestamp}}</div>
                </div>
            </div>
        </div>
        
        <!-- Action Section -->
        <div class="action-section">
            <h3 class="action-title">Recommended Action</h3>
            <p class="action-message">{{config.action}}</p>
            <a href="#" class="action-button">View Dashboard</a>
        </div>
        
        <!-- Footer -->
        <div class="email-footer">
            <p class="footer-text">
                This alert was generated by your Bitcoin Miner Monitor system.<br>
                Monitoring your mining operations 24/7 for optimal performance.
            </p>
            <div class="footer-links">
                <a href="#" class="footer-link">Dashboard</a>
                <a href="#" class="footer-link">Settings</a>
                <a href="#" class="footer-link">Support</a>
            </div>
            <p class="footer-text" style="margin-top: 15px; font-size: 11px;">
                © 2024 Bitcoin Miner Monitor. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        # Render the template
        template = self.jinja_env.from_string(html_template)
        return template.render(**template_data)
    
    async def _send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send an email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML)
            
        Returns:
            Result of sending the email
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.config['from_name']} <{self.config['from_address']}>"
            message["To"] = to_email
            
            # Add HTML body
            html_part = MIMEText(body, "html")
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.config["smtp_server"],
                port=self.config["smtp_port"],
                start_tls=self.config.get("use_tls", True),
                username=self.config["username"],
                password=self.config["password"],
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return {
                "success": True,
                "message": "Email sent successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e)
            }