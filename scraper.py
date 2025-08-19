"""Web scraper for educational reports using Playwright.

This module handles automated login and report downloading from an educational platform.
"""

import os
import sys
import time
import logging
import argparse
import json
from typing import List, Dict, Any, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
REPORTS_DIR = 'reports'
LOGIN_URL = 'https://accounts.learninga-z.com/ng/member/login?siteAbbr=rp'
USERNAME = os.getenv('SCRAPER_USERNAME', 'your_username')
PASSWORD = os.getenv('SCRAPER_PASSWORD', 'your_password')
CONFIG_FILE = 'scraper_config.json'
USERS_FILE = 'users.json'

# Page interaction timeouts
DEFAULT_TIMEOUT = 15000
LOGIN_TIMEOUT = 10000
DOWNLOAD_TIMEOUT = 30000

TABS = [
    {"name": "Student Usage"},
    {"name": "Skill"},
    {"name": "Assignment"},
    {"name": "Assessment"},
    {"name": "Level Up Progress"},
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_users(users_file: str = USERS_FILE) -> List[Dict[str, str]]:
    """Load users from JSON file.
    
    Args:
        users_file: Path to users JSON file
        
    Returns:
        List of user dictionaries with username and password
    """
    from utils import load_json
    users = load_json(users_file, [])
    logger.info(f"Loaded {len(users)} users from {users_file}")
    return users

def login(page, username: str, password: str) -> bool:
    """Perform login to the educational platform.
    
    Args:
        page: Playwright page object
        username: User's login username
        password: User's login password
        
    Returns:
        True if login successful, False otherwise
    """
    try:
        logger.info(f"Attempting login for user: {username}")
        logger.debug("Navigating to login page")
        page.goto(LOGIN_URL)
        
        logger.debug("Filling in credentials")
        page.fill('input#username', username)
        page.fill('input#password', password)
        
        logger.debug("Waiting for login button to be enabled")
        page.wait_for_selector(
            'button#memberLoginSubmitButton:not([disabled])', 
            timeout=LOGIN_TIMEOUT
        )
        
        logger.debug("Clicking login button")
        page.click('button#memberLoginSubmitButton')
        page.wait_for_load_state('networkidle')
        
        # Check if login was successful
        current_url = page.url
        logger.debug(f"Post-login URL: {current_url}")
        
        if current_url.startswith(LOGIN_URL):
            logger.error(f"Login failed for {username}: Still on login page")
            return False
            
        logger.info(f"Login successful for user: {username}")
        return True
        
    except PlaywrightTimeoutError as e:
        logger.error(f"Login timeout for {username}: {e}")
        return False
    except Exception as e:
        logger.error(f"Login error for {username}: {e}")
        return False

def navigate_to_reports(page) -> bool:
    """Navigate to the reports section of the platform.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if navigation successful, False otherwise
    """
    try:
        logger.debug("Looking for Menu button")
        page.wait_for_selector('span.buttonText', timeout=DEFAULT_TIMEOUT)
        
        menu_buttons = page.locator('span.buttonText')
        menu_found = False
        
        for i in range(menu_buttons.count()):
            if menu_buttons.nth(i).inner_text().strip() == 'Menu':
                logger.debug("Clicking Menu button")
                menu_buttons.nth(i).click()
                menu_found = True
                break
                
        if not menu_found:
            logger.error("Menu button not found")
            return False
            
        # Wait for menu to open
        time.sleep(2)
        
        logger.debug("Looking for Classroom Reports link")
        page.wait_for_selector('a:has-text("Classroom Reports")', timeout=DEFAULT_TIMEOUT)
        page.click('a:has-text("Classroom Reports")')
        page.wait_for_load_state('networkidle')
        
        current_url = page.url
        logger.info(f"Successfully navigated to reports section: {current_url}")
        time.sleep(3)  # Allow page to fully load
        return True
        
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout while navigating to reports: {e}")
        return False
    except Exception as e:
        logger.error(f"Error navigating to reports: {e}")
        return False

def select_date_filter(page, label: str) -> bool:
    """Select a date filter option from the dropdown.
    
    Args:
        page: Playwright page object
        label: Date filter label to select
        
    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.debug(f"Selecting date filter: {label}")
        
        # Click on the date filter dropdown
        page.wait_for_selector('#mat-select-0', timeout=DEFAULT_TIMEOUT)
        page.click('#mat-select-0')
        time.sleep(1)
        
        # Wait for options to appear and select the desired one
        page.wait_for_selector('mat-option .mat-option-text', timeout=DEFAULT_TIMEOUT)
        options = page.locator('mat-option .mat-option-text')
        
        option_found = False
        for i in range(options.count()):
            option_text = options.nth(i).inner_text().strip()
            if option_text == label:
                options.nth(i).click()
                logger.info(f"Selected date filter: {label}")
                option_found = True
                break
                
        if not option_found:
            logger.warning(f"Date filter option '{label}' not found")
            return False
            
        time.sleep(2)  # Allow filter to apply
        return True
        
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting date filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting date filter '{label}': {e}")
        return False

def download_report(page, username: str) -> bool:
    """Download the current report as CSV and convert to XLSX.
    
    Args:
        page: Playwright page object
        username: Username to include in filename for user differentiation
        
    Returns:
        True if download successful, False otherwise
    """
    try:
        # Check if there are any results to download
        no_results_locator = page.locator('text="No results for filter criteria"')
        if no_results_locator.count() > 0:
            logger.warning("No results for filter criteria, skipping download")
            return False
            
        logger.debug("Attempting to download report")
        
        # Click the options (ellipsis) button
        page.wait_for_selector('button[tid="class-reports-ellipsis-tooltip"]', timeout=DEFAULT_TIMEOUT)
        page.click('button[tid="class-reports-ellipsis-tooltip"]')
        time.sleep(1)
        
        # Download the CSV report
        logger.debug("Initiating CSV download")
        with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
            page.click('#report-menu-options-0-csv-report-download-btn')
            
        download = download_info.value
        original_filename = download.suggested_filename
        
        # Create user-specific filename by prepending username
        user_filename = f"{username}_{original_filename}"

        if getattr(sys, 'frozen', False):  # If running as a frozen executable
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')
        REPORTS_DIR_TMP = os.path.join(base_path, 'reports')

        csv_path = os.path.join(REPORTS_DIR_TMP, user_filename)
        
        download.save_as(csv_path)
        logger.info(f"Downloaded CSV report: {user_filename}")
        
        # Convert CSV to XLSX
        from utils import convert_csv_to_xlsx as utils_convert
        if utils_convert(csv_path):
            return True
        else:
            return False
        
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout during report download: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        return False

def switch_tab(page, tab_name: str) -> bool:
    """Switch to a specific report tab.
    
    Args:
        page: Playwright page object
        tab_name: Name of the tab to switch to
        
    Returns:
        True if tab switch successful, False otherwise
    """
    try:
        logger.debug(f"Switching to tab: {tab_name}")
        
        tab_buttons = page.locator('button[role="tab"]')
        tab_found = False
        available_tabs = []
        
        for i in range(tab_buttons.count()):
            button_text = tab_buttons.nth(i).inner_text().strip()
            available_tabs.append(button_text)
            
            if tab_name.lower() in button_text.lower():
                logger.debug(f"Clicking tab button: {button_text}")
                tab_buttons.nth(i).click()
                page.wait_for_load_state('networkidle')
                time.sleep(2)  # Allow tab content to load
                logger.info(f"Successfully switched to tab: {tab_name}")
                tab_found = True
                break
                
        if not tab_found:
            logger.error(f"Tab '{tab_name}' not found. Available tabs: {available_tabs}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error switching to tab '{tab_name}': {e}")
        return False


def get_config() -> Dict[str, Any]:
    """Load scraper configuration from file.
    
    Returns:
        Configuration dictionary with date_filter and tabs settings
    """
    default_config = {
        "date_filter": "Today",
        "tabs": {tab["name"]: True for tab in TABS}
    }
    
    from utils import load_json
    config = load_json(CONFIG_FILE, default_config)
    logger.info("Loaded scraper configuration")
    return config

def login_and_download_reports_for_user(username: str, password: str) -> bool:
    """Login and download reports for a specific user.
    
    Args:
        username: User's login username
        password: User's login password
        
    Returns:
        True if process completed successfully, False otherwise
    """
    logger.info(f"Starting report download process for user: {username}")
    
    try:
        # Check if the application is running in a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # For PyInstaller, check multiple possible locations
            possible_paths = [
                os.path.join(sys._MEIPASS, 'playwright'),  # Bundled in _internal
                os.path.join(os.path.dirname(sys.executable), 'playwright'),  # Next to exe
                os.path.join(os.path.dirname(sys.executable), '_internal', 'playwright'),  # In _internal folder
            ]
            
            bundled_playwright_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    bundled_playwright_path = path
                    logger.info(f"Found playwright browsers at: {path}")
                    break
            
            if not bundled_playwright_path:
                logger.error(f"Could not find playwright browsers. Checked paths: {possible_paths}")
                raise FileNotFoundError("Playwright browsers not found in executable bundle")
        else:
            # Path for a normal Python environment
            bundled_playwright_path = os.path.join(os.getcwd(), 'playwright')
            if not os.path.exists(bundled_playwright_path):
                logger.warning(f"Local playwright directory not found: {bundled_playwright_path}")

        # Set the environment variable so Playwright knows where to look.
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = bundled_playwright_path
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to: {bundled_playwright_path}")


        with sync_playwright() as p:
            # Launch browser with proper configuration
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            try:
                # Perform login
                if not login(page, username, password):
                    logger.error(f"Login failed for user: {username}")
                    return False
                    
                # Navigate to reports section
                if not navigate_to_reports(page):
                    logger.error(f"Failed to navigate to reports for user: {username}")
                    return False
                    
                # Load configuration
                config = get_config()
                selected_filter = config.get('date_filter', 'Today')
                selected_tabs = config.get('tabs', {tab["name"]: True for tab in TABS})
                
                logger.info(f"Using date filter: {selected_filter}")
                
                # Process each tab
                successful_downloads = 0
                total_tabs = sum(1 for tab in TABS if selected_tabs.get(tab["name"], True))
                
                for tab in TABS:
                    tab_name = tab["name"]
                    
                    if not selected_tabs.get(tab_name, True):
                        logger.info(f"Skipping {tab_name} report (not selected)")
                        continue
                    
                    logger.info(f"Processing {tab_name} report")
                    
                    try:
                        if switch_tab(page, tab_name):
                            if download_report(page, username):
                                successful_downloads += 1
                                logger.info(f"Successfully downloaded {tab_name} report")
                            else:
                                logger.warning(f"Failed to download {tab_name} report")
                        else:
                            logger.warning(f"Failed to switch to {tab_name} tab")
                    except Exception as e:
                        logger.error(f"Error processing {tab_name} report: {e}")
                        
                logger.info(f"Completed report download for {username}: {successful_downloads}/{total_tabs} successful")
                return successful_downloads > 0
                
            finally:
                browser.close()
                
    except Exception as e:
        logger.error(f"Unexpected error during report download for {username}: {e}")
        return False

def run_scraper_for_users(users_file: str = USERS_FILE, verbose: bool = False) -> bool:
    """Run the scraper for all users in the users file.
    
    Args:
        users_file: Path to users JSON file
        verbose: Enable verbose logging
        
    Returns:
        True if at least one user was processed successfully, False otherwise
    """
    # Set logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    logger.info("Starting scraper execution")
    
    # Load users
    users = load_users(users_file)
    if not users:
        logger.error("No users found. Please check the users file.")
        return False
    
    logger.info(f"Found {len(users)} users to process")
    
    # Process each user
    successful_users = 0
    for i, user in enumerate(users, 1):
        username = user.get('username')
        password = user.get('password')
        
        if not username or not password:
            logger.error(f"User {i}: Missing username or password, skipping")
            continue
            
        logger.info(f"Processing user {i}/{len(users)}: {username}")
        
        try:
            if login_and_download_reports_for_user(username, password):
                successful_users += 1
                logger.info(f"Successfully processed user: {username}")
            else:
                logger.error(f"Failed to process user: {username}")
        except Exception as e:
            logger.error(f"Unexpected error processing user {username}: {e}")
    
    logger.info(f"Scraper completed: {successful_users}/{len(users)} users processed successfully")
    return successful_users > 0

def main() -> None:
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Educational platform report scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--users', 
        type=str, 
        default=USERS_FILE, 
        help='Path to users JSON file containing login credentials'
    )
    parser.add_argument(
        '--verbose', 
        '-v', 
        action='store_true', 
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        default=CONFIG_FILE, 
        help='Path to scraper configuration file'
    )
    
    args = parser.parse_args()
    
    # Run the scraper
    success = run_scraper_for_users(args.users, args.verbose)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        raise 
