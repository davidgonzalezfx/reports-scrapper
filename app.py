"""Flask web application for reports scraping management."""

from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify, send_file
import os
import threading
import logging
import webbrowser
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from waitress import serve

from utils import load_json, save_json, validate_filename, validate_user_data, get_report_files

# Constants
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

class AppState:
    """Application state management."""
    
    def __init__(self):
        self.download_in_progress = False
        self._lock = threading.Lock()
    
    def set_download_status(self, status: bool) -> None:
        """Thread-safe setter for download status."""
        with self._lock:
            self.download_in_progress = status
    
    def get_download_status(self) -> bool:
        """Thread-safe getter for download status."""
        with self._lock:
            return self.download_in_progress

app_state = AppState()

def save_config(config_data: Dict[str, Any]) -> None:
    """Save configuration data to file."""
    if not save_json(config_data, CONFIG_FILE):
        raise OSError("Failed to save configuration")
    logger.info("Configuration saved successfully")

def load_config() -> Dict[str, Any]:
    """Load configuration from file with fallback to defaults."""
    default_config = {
        "date_filter": DATE_FILTERS[0], 
        "tabs": {tab["name"]: tab["default"] for tab in TABS}
    }
    
    config = load_json(CONFIG_FILE, default_config)
    if config == default_config:
        logger.info("Using default configuration")
    else:
        logger.info("Configuration loaded successfully")
    return config

def load_users() -> List[Dict[str, str]]:
    """Load users from file with fallback to empty list."""
    users = load_json(USERS_FILE, [])
    logger.info(f"Loaded {len(users)} users successfully")
    return users

def save_users(users: List[Dict[str, str]]) -> None:
    """Save users to file."""
    if not save_json(users, USERS_FILE):
        raise OSError("Failed to save users")
    logger.info(f"Saved {len(users)} users successfully")

def run_scraper() -> None:
    """Execute the scraper directly by importing and calling the scraper module."""
    try:
        app_state.set_download_status(True)
        logger.info("Starting scraper process")
        
        users = load_users()
        if not users:
            logger.warning("No users found, scraper may not function properly")
        
        # Import scraper module and call directly
        try:
            from scraper import run_scraper_for_users
            success = run_scraper_for_users(USERS_FILE, verbose=False)
            
            if success:
                logger.info("Scraper completed successfully")
            else:
                logger.error("Scraper failed - no users processed successfully")
                
        except ImportError as e:
            logger.error(f"Failed to import scraper module: {e}")
        except Exception as e:
            logger.error(f"Error in scraper execution: {e}")
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
    finally:
        app_state.set_download_status(False)
        logger.info("Scraper process finished")

def parse_file_info(filename: str) -> Dict[str, str]:
    """Parse user and report information from filename.
    
    Args:
        filename: The filename to parse (format: username_originalfilename.xlsx)
        
    Returns:
        Dictionary with user, report_name, and original filename
    """
    try:
        name_without_ext = filename.rsplit('.', 1)[0]
        parts = name_without_ext.split('_', 1)
        
        if len(parts) == 2:
            username, report_name = parts
            
            # Check if this is a legacy file (starts with known report type)
            legacy_prefixes = ['Student Usage', 'Skill', 'Assignment', 'Assessment', 'Level Up Progress']
            if any(name_without_ext.startswith(prefix) for prefix in legacy_prefixes):
                return {'user': 'Unknown', 'report_name': name_without_ext, 'filename': filename}
            
            return {'user': username, 'report_name': report_name, 'filename': filename}
        
        # Single part or no underscore - treat as legacy
        return {'user': 'Unknown', 'report_name': name_without_ext, 'filename': filename}
        
    except Exception as e:
        logger.warning(f"Error parsing filename {filename}: {e}")
        return {'user': 'Unknown', 'report_name': filename.rsplit('.', 1)[0], 'filename': filename}

@app.route('/', methods=['GET'])
def index():
    """Main page displaying reports and configuration."""
    try:
        if getattr(sys, 'frozen', False):  # If running as a frozen executable
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')  
        REPORTS_DIR_TMP = os.path.join(base_path, 'reports')  # Adjust based on how reports are bundled
        raw_files = get_report_files(REPORTS_DIR_TMP)
        
        # Parse file information for better display
        files_with_info = [parse_file_info(f) for f in raw_files]
        
        # Group files by user for better organization
        files_by_user = {}
        for file_info in files_with_info:
            user = file_info['user']
            if user not in files_by_user:
                files_by_user[user] = []
            files_by_user[user].append(file_info)
        
        config = load_config()
        selected_filter = config.get('date_filter', DATE_FILTERS[0])
        selected_tabs = config.get('tabs', {tab["name"]: tab["default"] for tab in TABS})
        users = load_users()
        
        return render_template(
            'scrapper.html', 
            files=raw_files,  # Keep for backward compatibility
            files_with_info=files_with_info,
            files_by_user=files_by_user,
            download_in_progress=app_state.get_download_status(),
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
    """Update filter configuration from form data."""
    try:
        config = load_config()
        
        # Update date filter
        date_filter = request.form.get('date_filter', DATE_FILTERS[0])
        if date_filter not in DATE_FILTERS:
            logger.warning(f"Invalid date filter received: {date_filter}")
            date_filter = DATE_FILTERS[0]
        config['date_filter'] = date_filter
        
        # Update tabs selection
        selected_tabs = request.form.getlist('tabs')
        tabs_config = {tab["name"]: (tab["name"] in selected_tabs) for tab in TABS}
        config['tabs'] = tabs_config
        
        save_config(config)
        logger.info(f"Filter configuration updated: {date_filter}, tabs: {selected_tabs}")
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error updating filter configuration: {e}")
        return jsonify({'error': 'Failed to update configuration'}), 500

@app.route('/download/<filename>')
def download(filename: str):
    """Download a specific report file.
    
    Args:
        filename: Name of the file to download
    """
    if getattr(sys, 'frozen', False):  # If running as a frozen executable
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath('.')
    REPORTS_DIR_TMP = os.path.join(base_path, 'reports')  # Adjust based on how reports are bundled

    try:
        # Security check: ensure filename doesn't contain path traversal
        if not validate_filename(filename):
            logger.warning(f"Potentially malicious filename requested: {filename}")
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(REPORTS_DIR_TMP, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Requested file not found: {filename}")
            return jsonify({'error': 'File not found'}), 404

        logger.info(f"Downloading file: {filename}")
        return send_from_directory(REPORTS_DIR_TMP, filename, as_attachment=True)

    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/download-all-zip')
def download_all_zip():
    """Create and download a zip file containing all reports."""
    import tempfile
    import zipfile
    
    try:
        files = get_report_files(REPORTS_DIR)
        
        if not files:
            logger.info("No files available for zip download")
            return jsonify({'error': 'No files available for download'}), 404
        
        # Create a temporary zip file (using original approach)
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_path = os.path.join(REPORTS_DIR, file)
                    if os.path.exists(file_path):
                        zipf.write(file_path, file)
                        logger.debug(f"Added {file} to zip")
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f'reports_{timestamp}.zip'
            
            logger.info(f"Created zip file with {len(files)} reports: {zip_filename}")
            
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
                    logger.debug(f"Cleaned up temporary zip file: {temp_zip.name}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temp file {temp_zip.name}: {e}")
            threading.Thread(target=cleanup).start()
            
    except Exception as e:
        logger.error(f"Error creating zip download: {e}")
        return jsonify({'error': 'Failed to create zip file'}), 500

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start the scraping process."""
    try:
        if not app_state.get_download_status():
            logger.info("Starting new scrape job")
            threading.Thread(target=run_scraper, daemon=True).start()
            return jsonify({'status': 'started'})
        else:
            logger.info("Scrape request received but job already running")
            return jsonify({'status': 'already_running'})
    except Exception as e:
        logger.error(f"Error starting scrape job: {e}")
        return jsonify({'error': 'Failed to start scraper'}), 500

@app.route('/scrape-status')
def scrape_status():
    """Get current scraping status."""
    try:
        return jsonify({'in_progress': app_state.get_download_status()})
    except Exception as e:
        logger.error(f"Error getting scrape status: {e}")
        return jsonify({'error': 'Failed to get status'}), 500

@app.route('/get-users', methods=['GET'])
def get_users():
    """Get list of configured users."""
    try:
        users = load_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to load users'}), 500

@app.route('/save-users', methods=['POST'])
def save_users_route():
    """Save users configuration via JSON API."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        users = request.json.get('users', [])
        
        # Validate users data
        if not isinstance(users, list):
            return jsonify({'error': 'Users must be a list'}), 400
            
        for user in users:
            if not validate_user_data(user):
                return jsonify({'error': 'Each user must have username and password fields'}), 400
        
        save_users(users)
        logger.info(f"Saved {len(users)} users via API")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error saving users: {e}")
        return jsonify({'error': 'Failed to save users'}), 500

@app.route('/upload-users', methods=['POST'])
def upload_users():
    """Upload users configuration from JSON file."""
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
        try:
            import json
            users_data = json.loads(file_content)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON file format'}), 400
        
        # Validate the JSON structure
        if not isinstance(users_data, list):
            return jsonify({'error': 'JSON file must contain an array of users'}), 400
        
        for user in users_data:
            if not validate_user_data(user):
                return jsonify({'error': 'Each user must have username and password fields'}), 400
        
        # Save the new users configuration
        save_users(users_data)
        logger.info(f"Successfully uploaded {len(users_data)} users from file")
        return jsonify({'status': 'ok', 'message': f'Successfully uploaded {len(users_data)} users'})
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in uploaded file: {e}")
        return jsonify({'error': 'Invalid JSON file format'}), 400
    except UnicodeDecodeError as e:
        logger.error(f"File encoding error: {e}")
        return jsonify({'error': 'File encoding not supported, please use UTF-8'}), 400
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

def cleanup_reports_directory() -> None:
    """Clean up the reports directory on startup."""
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Delete all files in the reports directory
        files_removed = 0
        for f in os.listdir(REPORTS_DIR):
            file_path = os.path.join(REPORTS_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_removed += 1
        
        if files_removed > 0:
            logger.info(f"Cleaned up {files_removed} files from reports directory")
        else:
            logger.info("Reports directory is clean")
            
    except Exception as e:
        logger.error(f"Error cleaning up reports directory: {e}")

def open_browser(host: str = 'localhost', port: int = 5000, delay: float = 1.5) -> None:
    """Open the default web browser to the application URL.
    
    Args:
        host: Host address (use localhost for browser access)
        port: Port number
        delay: Delay in seconds before opening browser
    """
    def _open_browser():
        time.sleep(delay)  # Wait for server to start
        url = f"http://{host}:{port}"
        try:
            logger.info(f"Opening browser to {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")
            logger.info(f"Please open your browser manually and go to {url}")
    
    # Run in a separate thread to avoid blocking the server
    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()

if __name__ == '__main__':
    # Configuration
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # Server binds to all interfaces
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    BROWSER_HOST = 'localhost'  # Browser should connect to localhost
    AUTO_OPEN_BROWSER = os.getenv('AUTO_OPEN_BROWSER', 'true').lower() == 'true'
    
    cleanup_reports_directory()
    logger.info("Starting Flask application")
    logger.info(f"Server will be available at http://{BROWSER_HOST}:{PORT}")
    
    # Start browser opening in background (if enabled)
    if AUTO_OPEN_BROWSER:
        open_browser(host=BROWSER_HOST, port=PORT)
        logger.info("Browser will open automatically in 1.5 seconds...")
    else:
        logger.info("Auto-open browser disabled. Open your browser manually.")
    
    # Start the server
    try:
        serve(app, host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
