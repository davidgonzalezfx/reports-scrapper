#!/usr/bin/env python3
"""
Reports Scrapper Application - External Environment Version

This version is designed to work with externally installed Playwright
(via setup.sh/setup.bat) instead of trying to package it with the executable.
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

def find_python_executable():
    """Find the Python executable that has Playwright installed."""
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.info("✅ Running in virtual environment")
        return sys.executable
    
    # Check for playwright_env in current directory
    current_dir = Path(os.getcwd())
    venv_paths = [
        current_dir / "playwright_env" / "bin" / "python",  # Unix
        current_dir / "playwright_env" / "Scripts" / "python.exe",  # Windows
    ]
    
    for venv_path in venv_paths:
        if venv_path.exists():
            logger.info(f"✅ Found Python environment: {venv_path}")
            return str(venv_path)
    
    # Fall back to system Python
    logger.warning("⚠️  No virtual environment found, using system Python")
    return sys.executable

def check_playwright_availability():
    """Check if Playwright is available in the current Python environment."""
    python_exe = find_python_executable()
    
    try:
        # Test if Playwright is available
        result = subprocess.run([
            python_exe, "-c", 
            "from playwright.sync_api import sync_playwright; print('Playwright available')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.info("✅ Playwright is available")
            return True
        else:
            logger.error(f"❌ Playwright not available: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking Playwright: {e}")
        return False

def test_playwright_browser():
    """Test if Playwright browser is working."""
    python_exe = find_python_executable()
    
    test_script = '''
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com")
        title = page.title()
        browser.close()
        print(f"Browser test successful: {title}")
except Exception as e:
    print(f"Browser test failed: {e}")
    raise
'''
    
    try:
        result = subprocess.run([
            python_exe, "-c", test_script
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ Playwright browser test successful")
            logger.info(f"Browser output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Browser test failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing browser: {e}")
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
    """Run the scraper using external Python environment."""
    global download_in_progress
    download_in_progress = True
    users = load_users()
    
    try:
        logger.info("🤖 Starting scraper execution...")
        logger.info(f"📋 Found {len(users)} users to process")
        
        if not users:
            logger.warning("⚠️  No users configured - scraping aborted")
            return
        
        # Find the Python executable with Playwright
        python_exe = find_python_executable()
        
        # Run the scraper as a separate Python process
        scraper_script = os.path.join(os.getcwd(), 'scraper.py')
        
        if not os.path.exists(scraper_script):
            logger.error(f"❌ Scraper script not found: {scraper_script}")
            return
        
        # Run scraper with external Python
        cmd = [python_exe, scraper_script, '--users', USERS_FILE]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("✅ Scraper execution completed successfully")
            if result.stdout:
                logger.info(f"Scraper output: {result.stdout}")
        else:
            logger.error(f"❌ Scraper failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Scraper timed out after 30 minutes")
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        import traceback
        logger.error("📊 Full error traceback:")
        logger.error(traceback.format_exc())
    finally:
        download_in_progress = False
        logger.info("🔄 Scraper status reset")

# Flask routes (same as before)
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

@app.route('/set-filter', methods=['POST'])
def set_filter():
    """Update filter configuration."""
    try:
        config = load_config()
        
        date_filter = request.form.get('date_filter', DATE_FILTERS[0])
        if date_filter in DATE_FILTERS:
            config['date_filter'] = date_filter
        
        selected_tabs = request.form.getlist('tabs')
        tabs_config = {tab["name"]: (tab["name"] in selected_tabs) for tab in TABS}
        config['tabs'] = tabs_config
        
        save_config(config)
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in set_filter route: {e}")
        return jsonify({'error': 'Failed to update filter'}), 500

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start the scraping process."""
    global download_in_progress
    logger.info("🔍 Scrape request received")
    
    try:
        if not download_in_progress:
            # Check if Playwright is available before starting
            if not check_playwright_availability():
                return jsonify({
                    'status': 'error', 
                    'message': 'Playwright not available. Please run setup.sh/setup.bat first.'
                }), 500
            
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
        
        file_content = file.read().decode('utf-8')
        users_data = json.loads(file_content)
        
        if not isinstance(users_data, list):
            return jsonify({'error': 'JSON file must contain an array of users'}), 400
        
        for user in users_data:
            if not isinstance(user, dict) or 'username' not in user or 'password' not in user:
                return jsonify({'error': 'Each user must have username and password fields'}), 400
        
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

@app.route('/download-all-zip')
def download_all_zip():
    """Download all report files as a ZIP archive."""
    try:
        if not os.path.exists(REPORTS_DIR):
            return jsonify({'error': 'Reports directory not found'}), 404
        
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')]
        
        if not files:
            return jsonify({'error': 'No files available for download'}), 404
        
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_path = os.path.join(REPORTS_DIR, file)
                    if os.path.exists(file_path):
                        zipf.write(file_path, file)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f'reports_{timestamp}.zip'
            
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        finally:
            def cleanup():
                try:
                    os.unlink(temp_zip.name)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            threading.Thread(target=cleanup, daemon=True).start()
            
    except Exception as e:
        logger.error(f"Error creating ZIP download: {e}")
        return jsonify({'error': 'Failed to create ZIP file'}), 500

@app.route('/system-check')
def system_check():
    """Check system dependencies."""
    try:
        playwright_available = check_playwright_availability()
        browser_working = test_playwright_browser() if playwright_available else False
        
        return jsonify({
            'playwright_available': playwright_available,
            'browser_working': browser_working,
            'python_executable': find_python_executable(),
            'setup_recommended': not (playwright_available and browser_working)
        })
    except Exception as e:
        logger.error(f"Error in system check: {e}")
        return jsonify({'error': 'System check failed'}), 500

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
        
        # Check system dependencies
        logger.info("🔍 Checking system dependencies...")
        playwright_available = check_playwright_availability()
        
        if not playwright_available:
            logger.warning("⚠️  Playwright not available!")
            logger.warning("💡 Please run setup.sh (Mac/Linux) or setup.bat (Windows) first")
            logger.warning("🌐 The web interface will still start, but scraping will not work")
        else:
            logger.info("✅ Playwright is available")
            browser_working = test_playwright_browser()
            if not browser_working:
                logger.warning("⚠️  Playwright browsers may not be properly installed")
                logger.warning("💡 Please run setup.sh (Mac/Linux) or setup.bat (Windows) to fix this")
        
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