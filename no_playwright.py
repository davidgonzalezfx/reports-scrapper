#!/usr/bin/env python3
"""
Version of the application without Playwright imports at module level

This allows PyInstaller to build without auto-discovering Playwright browsers.
Playwright will be imported dynamically at runtime.
"""

import os
import sys
import subprocess
import threading
import json
import zipfile
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify, send_file
from waitress import serve
import webbrowser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

logger.info("🚀 Starting Reports Scrapper...")
logger.info("📦 Loading dependencies...")
logger.info("⚙️  Initializing Flask application...")

# Configuration constants
USERS_FILE = 'users.json'
REPORTS_DIR = 'reports'
CONFIG_FILE = 'scraper_config.json'

DATE_FILTERS = ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
TABS = [
    {"name": "Student Usage", "default": True},
    {"name": "Skill", "default": True},
    {"name": "Assignment", "default": True},
    {"name": "Assessment", "default": True},
    {"name": "Level Up Progress", "default": True},
]

# Initialize Flask app
app = Flask(__name__)

# Global state
download_in_progress = False

def check_playwright_readiness() -> bool:
    """Check if Playwright is available and install browsers if needed."""
    try:
        # Dynamic import to avoid PyInstaller auto-discovery
        import importlib
        playwright = importlib.import_module('playwright.sync_api')
        sync_playwright = playwright.sync_playwright
        
        # Try to use Playwright browsers
        with sync_playwright() as p:
            browser_types = ['chromium']
            available_browsers = []
            
            for browser_type in browser_types:
                try:
                    browser = getattr(p, browser_type)
                    browser_instance = browser.launch(headless=True)
                    browser_instance.close()
                    available_browsers.append(browser_type)
                    logger.info(f"✅ {browser_type} browser is ready")
                except Exception as browser_error:
                    logger.warning(f"⚠️  {browser_type} browser not available: {browser_error}")
                    logger.info(f"🔧 Attempting to install {browser_type}...")
                    
                    if install_playwright_browsers():
                        try:
                            browser_instance = browser.launch(headless=True)
                            browser_instance.close()
                            available_browsers.append(browser_type)
                            logger.info(f"✅ {browser_type} browser installed and verified")
                        except Exception as retry_error:
                            logger.error(f"❌ {browser_type} still not working after installation: {retry_error}")
            
            if available_browsers:
                logger.info(f"✅ Playwright ready with browsers: {', '.join(available_browsers)}")
                return True
            else:
                logger.error("❌ No Playwright browsers available after installation attempts")
                return False
                
    except ImportError as e:
        logger.error(f"❌ Playwright module not found: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Playwright initialization failed: {e}")
        return False

def install_playwright_browsers() -> bool:
    """Install Playwright browsers without requiring external Python/pip."""
    logger.info("🔧 Installing Playwright browsers automatically...")
    
    install_commands = [
        [sys.executable, "-m", "playwright", "install", "chromium"],
        ["playwright", "install", "chromium"]
    ]
    
    for cmd in install_commands:
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("✅ Playwright browsers installed successfully")
                return True
            else:
                logger.warning(f"Installation command failed: {result.stderr}")
                
        except Exception as e:
            logger.warning(f"Installation attempt failed: {e}")
            continue
    
    logger.error("❌ Failed to install Playwright browsers")
    return False

def save_config(config_data: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {CONFIG_FILE}")
                return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
    
    default_config = {
        "date_filter": DATE_FILTERS[0], 
        "tabs": {tab["name"]: tab["default"] for tab in TABS}
    }
    logger.info("Using default configuration")
    return default_config

def load_users() -> List[Dict[str, str]]:
    """Load users from file."""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)
                logger.info(f"Loaded {len(users)} users from {USERS_FILE}")
                return users
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
    
    logger.info("No users file found, returning empty list")
    return []

def save_users(users: List[Dict[str, str]]) -> None:
    """Save users to file."""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        logger.info(f"Saved {len(users)} users to {USERS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save users: {e}")

def run_scraper() -> None:
    """Run the scraper in a separate thread."""
    global download_in_progress
    download_in_progress = True
    users = load_users()
    
    try:
        logger.info("🤖 Starting scraper execution...")
        logger.info(f"📋 Found {len(users)} users to process")
        
        if not users:
            logger.warning("⚠️  No users configured - scraping aborted")
            return
        
        # Dynamic import of scraper module
        import importlib
        scraper_module = importlib.import_module('scraper')
        
        scraper_module.main(['--users', USERS_FILE])
        logger.info("✅ Scraper execution completed successfully")
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        import traceback
        logger.error("📊 Full error traceback:")
        logger.error(traceback.format_exc())
    finally:
        download_in_progress = False
        logger.info("🔄 Scraper status reset")

# Flask routes
@app.route('/', methods=['GET'])
def index():
    """Main application route."""
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')] if os.path.exists(REPORTS_DIR) else []
        files.sort(reverse=True)
        
        config = load_config()
        selected_filter = config.get('date_filter', DATE_FILTERS[0])
        selected_tabs = config.get('tabs', {tab["name"]: tab["default"] for tab in TABS})
        users = load_users()
        
        return render_template(
            'scrapper.html', 
            files=files, 
            download_in_progress=download_in_progress,
            date_filters=DATE_FILTERS, 
            selected_filter=selected_filter,
            tabs=TABS, 
            selected_tabs=selected_tabs, 
            users=users
        )
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start the scraping process."""
    global download_in_progress
    logger.info("🔍 Scrape request received")
    
    try:
        if not download_in_progress:
            logger.info("🚀 Starting new scraper thread...")
            threading.Thread(target=run_scraper, daemon=True).start()
            logger.info("✅ Scraper thread started successfully")
            return jsonify({'status': 'started'})
        else:
            logger.warning("⚠️  Scraper already running")
            return jsonify({'status': 'already_running'})
    except Exception as e:
        logger.error(f"❌ Error starting scraper: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/scrape-status')
def scrape_status():
    """Get current scraping status."""
    return jsonify({'in_progress': download_in_progress})

# Add other routes (simplified for brevity)
@app.route('/download/<filename>')
def download(filename: str):
    """Download a specific report file."""
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = os.path.join(REPORTS_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_from_directory(REPORTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({'error': 'Download failed'}), 500

def open_browser() -> None:
    """Open browser after a short delay to ensure server is running."""
    import time
    logger.info("🌐 Preparing to open browser...")
    time.sleep(2)
    logger.info("🔗 Opening browser at http://localhost:5000")
    try:
        webbrowser.open('http://localhost:5000')
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")

def main() -> None:
    """Main application entry point."""
    logger.info("📍 Current working directory: %s", os.getcwd())
    logger.info("📁 Setting up reports directory...")
    
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        logger.info("🧹 Cleaning previous reports directory...")
        if os.path.exists(REPORTS_DIR):
            for f in os.listdir(REPORTS_DIR):
                file_path = os.path.join(REPORTS_DIR, f)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")
        
        logger.info("📂 Reports directory ready at: %s", os.path.abspath(REPORTS_DIR))
        
        logger.info("🌍 Starting web server...")
        threading.Thread(target=open_browser, daemon=True).start()
        
        logger.info("🎯 Server starting on http://localhost:5000")
        logger.info("💡 The application will open automatically in your browser")
        logger.info("📱 If browser doesn't open, visit: http://localhost:5000")
        logger.info("-" * 50)
        
        serve(app, host='0.0.0.0', port=5000)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()