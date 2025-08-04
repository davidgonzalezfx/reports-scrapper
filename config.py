"""Configuration management for the reports scraper application.

This module provides centralized configuration handling for all components
of the reports scraper system.
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / 'reports'
LOGS_DIR = PROJECT_ROOT / 'logs'
CONFIG_DIR = PROJECT_ROOT

# Ensure directories exist
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# File paths
USERS_FILE = CONFIG_DIR / 'users.json'
SCRAPER_CONFIG_FILE = CONFIG_DIR / 'scraper_config.json'

# Application constants
DATE_FILTERS = ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
TABS = [
    {"name": "Student Usage", "default": True},
    {"name": "Skill", "default": True},
    {"name": "Assignment", "default": True},
    {"name": "Assessment", "default": True},
    {"name": "Level Up Progress", "default": True},
]

# Web scraping constants
LOGIN_URL = 'https://accounts.learninga-z.com/ng/member/login?siteAbbr=rp'
DEFAULT_TIMEOUT = 15000
LOGIN_TIMEOUT = 10000
DOWNLOAD_TIMEOUT = 30000
SCRAPER_TIMEOUT = 3600

# Flask configuration
FLASK_CONFIG = {
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production'),
    'HOST': os.getenv('FLASK_HOST', '0.0.0.0'),
    'PORT': int(os.getenv('FLASK_PORT', '5000')),
    'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
}

# Scheduler configuration
SCHEDULER_CONFIG = {
    'DEFAULT_INTERVAL_WEEKS': int(os.getenv('SCHEDULER_INTERVAL_WEEKS', '1')),
    'JOB_DEFAULTS': {
        'coalesce': False,
        'max_instances': 1
    }
}

def setup_logging(
    name: str, 
    log_file: str = None, 
    level: int = logging.INFO,
    include_console: bool = True
) -> logging.Logger:
    """Setup standardized logging configuration.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Log file name (will be placed in logs directory)
        level: Logging level
        include_console: Whether to include console output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(LOGS_DIR / log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_browser_config() -> Dict[str, Any]:
    """Get browser configuration for Playwright.
    
    Returns:
        Dictionary with browser configuration options
    """
    return {
        'headless': os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true',
        'args': [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ],
        'user_agent': (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        'viewport': {'width': 1280, 'height': 800},
        'ignore_https_errors': True,
        'accept_downloads': True
    }

def validate_environment() -> bool:
    """Validate that the environment is properly configured.
    
    Returns:
        True if environment is valid, False otherwise
    """
    # Check for required directories
    required_dirs = [REPORTS_DIR, LOGS_DIR]
    for directory in required_dirs:
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(f"Failed to create directory {directory}: {e}")
                return False
    
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        return False
    
    return True

# Environment validation on import
if not validate_environment():
    raise RuntimeError("Environment validation failed")