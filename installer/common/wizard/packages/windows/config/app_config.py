"""
Bitcoin Solo Miner Monitoring App - Configuration

This file contains the main configuration settings for the application.
"""

from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Application settings
APP_NAME = "Bitcoin Solo Miner Monitoring App"
APP_VERSION = "0.1.0"
DEBUG = False

# Server settings
HOST = "0.0.0.0"  # bind to all interfaces for production deployment
PORT = 8000

# Database settings - paths will be resolved at runtime using AppPaths
DB_CONFIG = {
    "sqlite": {
        "path": "data/config.db"  # Relative path, will be resolved by AppPaths
    }
}

# Miner settings
DEFAULT_POLLING_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 10  # seconds - increased for real network conditions
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds - reduced for faster recovery

# Logging settings
LOG_LEVEL = "WARNING"
LOG_FILE = "logs/app.log"  # Relative path, will be resolved by AppPaths

# UI settings
THEME = "dark"
CHART_RETENTION_DAYS = 30
DEFAULT_REFRESH_INTERVAL = 10  # seconds

# Email settings
EMAIL_CONFIG = {
    "enabled": False,  # Disabled by default until configured
    "smtp_server": "",
    "smtp_port": 587,
    "username": "",
    "password": "",
    "use_tls": True,
    "from_address": "",
    "from_name": "Bitcoin Miner Monitor",
    "rate_limit": {
        "max_emails_per_hour": 10,
        "max_emails_per_day": 50
    }
}