#!/usr/bin/env python3
"""
Reports Scrapper Application

A Flask web application for scraping reports from Learning A-Z platform
using Playwright automation.
"""

import sys
import os
import subprocess
import threading
import json
import zipfile
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify, send_file
from waitress import serve
import webbrowser

import scraper

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
logger.info("🔧 Loading scraper module...")
logger.info("🎭 Checking Playwright installation...")

def install_playwright_browsers() -> bool:
    """Install Playwright browsers without requiring external Python/pip.
    
    Returns:
        bool: True if installation successful, False otherwise
    """
    logger.info("🔧 Installing Playwright browsers automatically...")
    try:
        from playwright.sync_api import sync_playwright
        
        # Try multiple installation methods
        methods = [
            ("driver_executable", install_via_driver_executable),
            ("python_module", install_via_python_module),
            ("force_download", install_via_force_download)
        ]
        
        for method_name, method_func in methods:
            try:
                logger.info(f"🔄 Trying installation method: {method_name}")
                if method_func():
                    logger.info(f"✅ Browser installed successfully via {method_name}")
                    return True
            except Exception as e:
                logger.warning(f"⚠️  Method {method_name} failed: {e}")
                continue
        
        logger.error("❌ All installation methods failed")
        return False
                
    except Exception as e:
        logger.error(f"❌ Browser installation failed: {e}")
        return False

def install_via_driver_executable() -> bool:
    """Install using Playwright driver executable.
    
    Returns:
        bool: True if installation successful
        
    Raises:
        Exception: If installation fails
    """
    from playwright._impl._driver import compute_driver_executable
    
    driver_executable = compute_driver_executable()
    if isinstance(driver_executable, tuple):
        driver_path = driver_executable[0] if driver_executable else None
    else:
        driver_path = driver_executable
    
    if not driver_path or not os.path.exists(driver_path):
        raise Exception("Driver executable not found")
    
    result = subprocess.run(
        [driver_path, "install", "chromium"], 
        capture_output=True, 
        text=True, 
        timeout=300
    )
    
    if result.returncode == 0:
        return True
    else:
        raise Exception(f"Driver installation failed: {result.stderr}")

def install_via_python_module() -> bool:
    """Install using Python module approach.
    
    Returns:
        bool: True if installation successful
        
    Raises:
        Exception: If installation fails
    """
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"], 
        capture_output=True, 
        text=True, 
        timeout=300
    )
    
    if result.returncode == 0:
        return True
    else:
        raise Exception(f"Python module installation failed: {result.stderr}")

def install_via_force_download() -> bool:
    """Force download via Playwright internal APIs.
    
    Returns:
        bool: True if installation successful
        
    Raises:
        Exception: If installation fails
    """
    from playwright.sync_api import sync_playwright
    
    # Try to force browser download by attempting launch
    with sync_playwright() as p:
        try:
            # This should trigger automatic download
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
        except Exception as e:
            # If it fails due to missing browser, try to force install
            logger.info(f"🔄 Launch failed, attempting force install: {e}")
            
            # Try accessing internal installation methods
            try:
                import playwright._impl._driver as driver_module
                # Use internal installation if available
                if hasattr(driver_module, 'install'):
                    driver_module.install(['chromium'])
                    return True
                else:
                    raise Exception("Internal install method not available")
            except Exception as internal_e:
                raise Exception(f"Force download failed: {internal_e}")

def check_playwright_readiness() -> bool:
    """Check if Playwright is available and install browsers if needed.
    
    Returns:
        bool: True if Playwright is ready, False otherwise
    """
    try:
        from playwright.sync_api import sync_playwright
        
        # Try to use Playwright browsers
        with sync_playwright() as p:
            browser_types = ['chromium']  # Focus on chromium for reliability
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
                        # Retry after installation
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

# Check Playwright readiness
playwright_ready = check_playwright_readiness()

if not playwright_ready:
    logger.warning("⚠️  Playwright not ready - web scraping functionality may be limited")
    logger.info("💡 The application will continue to run, but scraping may fail")

logger.info("✅ All modules loaded successfully!")

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

def save_config(config_data: Dict[str, Any]) -> None:
    """Save configuration to file.
    
    Args:
        config_data: Configuration dictionary to save
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")

def load_config() -> Dict[str, Any]:
    """Load configuration from file.
    
    Returns:
        Configuration dictionary with defaults if file doesn't exist
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {CONFIG_FILE}")
                return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
    
    # Return default configuration
    default_config = {
        "date_filter": DATE_FILTERS[0], 
        "tabs": {tab["name"]: tab["default"] for tab in TABS}
    }
    logger.info("Using default configuration")
    return default_config

def load_users() -> List[Dict[str, str]]:
    """Load users from file.
    
    Returns:
        List of user dictionaries
    """
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
    """Save users to file.
    
    Args:
        users: List of user dictionaries to save
    """
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
        
        # Ensure Playwright browsers are available before scraping
        logger.info("🎭 Verifying Playwright browsers before scraping...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
                logger.info("✅ Playwright browser verification successful")
        except Exception as browser_error:
            logger.warning(f"⚠️  Browser verification failed: {browser_error}")
            logger.info("🔧 Installing Playwright browsers...")
            if install_playwright_browsers():
                logger.info("✅ Browser installation completed, retrying verification...")
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        browser.close()
                        logger.info("✅ Browser verification successful after installation")
                except Exception as retry_error:
                    logger.error(f"❌ Browser still not working after installation: {retry_error}")
                    raise Exception("Playwright browsers are not available for scraping")
            else:
                raise Exception("Failed to install Playwright browsers")
            
        scraper.main(['--users', USERS_FILE])
        logger.info("✅ Scraper execution completed successfully")
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        import traceback
        logger.error("📊 Full error traceback:")
        logger.error(traceback.format_exc())
    finally:
        download_in_progress = False
        logger.info("🔄 Scraper status reset")

@app.route('/', methods=['GET'])
def index():
    """Main application route."""
    try:
        # Get report files
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')] if os.path.exists(REPORTS_DIR) else []
        files.sort(reverse=True)
        
        # Load configuration and users
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

@app.route('/set-filter', methods=['POST'])
def set_filter():
    """Update filter configuration."""
    try:
        config = load_config()
        
        # Update date filter
        date_filter = request.form.get('date_filter', DATE_FILTERS[0])
        if date_filter in DATE_FILTERS:
            config['date_filter'] = date_filter
        
        # Update tabs selection
        selected_tabs = request.form.getlist('tabs')
        tabs_config = {tab["name"]: (tab["name"] in selected_tabs) for tab in TABS}
        config['tabs'] = tabs_config
        
        save_config(config)
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in set_filter route: {e}")
        return jsonify({'error': 'Failed to update filter'}), 500

@app.route('/download/<filename>')
def download(filename: str):
    """Download a specific report file.
    
    Args:
        filename: Name of the file to download
    """
    try:
        # Security check: ensure filename is safe
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = os.path.join(REPORTS_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_from_directory(REPORTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/download-all-zip')
def download_all_zip():
    """Download all report files as a ZIP archive."""
    try:
        if not os.path.exists(REPORTS_DIR):
            return jsonify({'error': 'Reports directory not found'}), 404
        
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')]
        
        if not files:
            return jsonify({'error': 'No files available for download'}), 404
        
        # Create a temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_path = os.path.join(REPORTS_DIR, file)
                    if os.path.exists(file_path):
                        zipf.write(file_path, file)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f'reports_{timestamp}.zip'
            
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        finally:
            # Clean up temp file after sending
            def cleanup():
                try:
                    os.unlink(temp_zip.name)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            threading.Thread(target=cleanup, daemon=True).start()
            
    except Exception as e:
        logger.error(f"Error creating ZIP download: {e}")
        return jsonify({'error': 'Failed to create ZIP file'}), 500

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

@app.route('/get-users', methods=['GET'])
def get_users():
    """Get current users configuration."""
    try:
        users = load_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to load users'}), 500

@app.route('/save-users', methods=['POST'])
def save_users_route():
    """Save users configuration."""
    try:
        if not request.json:
            return jsonify({'error': 'No data provided'}), 400
        
        users = request.json.get('users', [])
        if not isinstance(users, list):
            return jsonify({'error': 'Users must be a list'}), 400
        
        # Validate user data
        for user in users:
            if not isinstance(user, dict) or 'username' not in user or 'password' not in user:
                return jsonify({'error': 'Each user must have username and password'}), 400
        
        save_users(users)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error saving users: {e}")
        return jsonify({'error': 'Failed to save users'}), 500

@app.route('/upload-users', methods=['POST'])
def upload_users():
    """Upload users from a JSON file."""
    try:
        if 'users_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['users_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be a JSON file'}), 400
        
        # Read and parse the uploaded JSON
        file_content = file.read().decode('utf-8')
        users_data = json.loads(file_content)
        
        # Validate the JSON structure
        if not isinstance(users_data, list):
            return jsonify({'error': 'JSON file must contain an array of users'}), 400
        
        for user in users_data:
            if not isinstance(user, dict) or 'username' not in user or 'password' not in user:
                return jsonify({'error': 'Each user must have username and password fields'}), 400
        
        # Save the new users configuration
        save_users(users_data)
        return jsonify({
            'status': 'ok', 
            'message': f'Successfully uploaded {len(users_data)} users'
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return jsonify({'error': 'Invalid JSON file format'}), 400
    except Exception as e:
        logger.error(f"Error uploading users: {e}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

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
        # Delete all files in the reports directory
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
        # Open browser in a separate thread
        threading.Thread(target=open_browser, daemon=True).start()
        
        logger.info("🎯 Server starting on http://localhost:5000")
        logger.info("💡 The application will open automatically in your browser")
        logger.info("📱 If browser doesn't open, visit: http://localhost:5000")
        logger.info("-" * 50)
        
        # Use production-ready server
        serve(app, host='0.0.0.0', port=5000)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
