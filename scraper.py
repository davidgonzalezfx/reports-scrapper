#!/usr/bin/env python3
"""
Web Scraper for Learning A-Z Reports

Automated scraper using Playwright to download reports from Learning A-Z platform.
"""

import os
import time
import json
import argparse
import logging
from typing import List, Dict, Any, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
REPORTS_DIR = 'reports'
LOGIN_URL = 'https://accounts.learninga-z.com/ng/member/login?siteAbbr=rp'
USERNAME = os.getenv('SCRAPER_USERNAME', 'your_username')
PASSWORD = os.getenv('SCRAPER_PASSWORD', 'your_password')
CONFIG_FILE = 'scraper_config.json'
USERS_FILE = 'users.json'

TABS = [
    {"name": "Student Usage"},
    {"name": "Skill"},
    {"name": "Assignment"},
    {"name": "Assessment"},
    {"name": "Level Up Progress"},
]

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_users(users_file: str = USERS_FILE) -> List[Dict[str, str]]:
    """Load users from JSON file.
    
    Args:
        users_file: Path to users JSON file
        
    Returns:
        List of user dictionaries with username and password
    """
    try:
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
                logger.info(f"Loaded {len(users)} users from {users_file}")
                return users
    except Exception as e:
        logger.error(f"Failed to load users from {users_file}: {e}")
    
    logger.warning("No users file found, returning empty list")
    return []

def login(page, username: str, password: str) -> bool:
    """Login to the Learning A-Z platform.
    
    Args:
        page: Playwright page object
        username: User's username
        password: User's password
        
    Returns:
        True if login successful, False otherwise
    """
    try:
        logger.info('Navigating to login page...')
        page.goto(LOGIN_URL)
        
        logger.info('Filling in username...')
        page.fill('input#username', username)
        
        logger.info('Filling in password...')
        page.fill('input#password', password)
        
        logger.info('Waiting for login button to be enabled...')
        page.wait_for_selector('button#memberLoginSubmitButton:not([disabled])', timeout=10000)
        
        logger.info('Clicking login button...')
        page.click('button#memberLoginSubmitButton')
        page.wait_for_load_state('networkidle')
        
        logger.info(f'After login, current URL: {page.url}')
        if page.url.startswith(LOGIN_URL):
            logger.error('Login failed: Still on login page.')
            return False
            
        logger.info('Login successful!')
        return True
        
    except PlaywrightTimeoutError as e:
        logger.error(f'Login failed due to timeout: {e}')
        return False
    except Exception as e:
        logger.error(f'Login failed with error: {e}')
        return False

def navigate_to_reports(page) -> bool:
    """Navigate to the Classroom Reports section.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if navigation successful, False otherwise
    """
    try:
        # Click Menu button
        page.wait_for_selector('span.buttonText', timeout=15000)
        menu_buttons = page.locator('span.buttonText')
        
        menu_clicked = False
        for i in range(menu_buttons.count()):
            if menu_buttons.nth(i).inner_text().strip() == 'Menu':
                logger.info('Clicking Menu button...')
                menu_buttons.nth(i).click()
                menu_clicked = True
                break
        
        if not menu_clicked:
            logger.error('Menu button not found')
            return False
            
        time.sleep(2)
        
        # Navigate to Classroom Reports
        logger.info('Looking for Classroom Reports link...')
        page.wait_for_selector('a:has-text("Classroom Reports")', timeout=15000)
        page.click('a:has-text("Classroom Reports")')
        page.wait_for_load_state('networkidle')
        
        logger.info(f'Navigated to Classroom Reports. Current URL: {page.url}')
        time.sleep(3)
        return True
        
    except Exception as e:
        logger.error(f'Navigation to reports failed: {e}')
        return False

def select_date_filter(page, label: str) -> bool:
    """Select a date filter option.
    
    Args:
        page: Playwright page object
        label: Date filter label to select
        
    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.info(f'Selecting date filter: {label}...')
        page.wait_for_selector('#mat-select-0', timeout=10000)
        page.click('#mat-select-0')
        time.sleep(1)
        
        page.wait_for_selector('mat-option .mat-option-text', timeout=10000)
        options = page.locator('mat-option .mat-option-text')
        
        option_selected = False
        for i in range(options.count()):
            if options.nth(i).inner_text().strip() == label:
                options.nth(i).click()
                logger.info(f'Selected "{label}" in date filter.')
                option_selected = True
                break
        
        if not option_selected:
            logger.error(f'Date filter option "{label}" not found')
            return False
            
        time.sleep(2)
        return True
        
    except Exception as e:
        logger.error(f'Could not select date filter {label}: {e}')
        return False

def download_report(page) -> bool:
    """Download a report from the current tab.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if download successful, False otherwise
    """
    try:
        # Check for 'No results for filter criteria' before attempting download
        if page.locator('text="No results for filter criteria"').count() > 0:
            logger.info('No results for filter criteria. Skipping download for this tab.')
            return False
            
        logger.info('Clicking options (ellipsis) button...')
        page.click('button[tid="class-reports-ellipsis-tooltip"]')
        time.sleep(1)
        
        logger.info('Clicking download button and waiting for download...')
        with page.expect_download() as download_info:
            page.click('#report-menu-options-0-csv-report-download-btn')
            
        download = download_info.value
        filename = download.suggested_filename
        csv_path = os.path.join(REPORTS_DIR, filename)
        download.save_as(csv_path)
        
        logger.info(f'Downloaded CSV to {csv_path}')
        convert_csv_to_xlsx(csv_path)
        return True
        
    except Exception as e:
        logger.error(f'Failed to download report: {e}')
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
        logger.info(f'Switching to tab: {tab_name}...')
        
        # Try by button text
        tab_buttons = page.locator('button[role="tab"]')
        found = False
        
        for i in range(tab_buttons.count()):
            text = tab_buttons.nth(i).inner_text().strip().lower()
            if tab_name.lower() in text:
                logger.info(f'Clicking tab button with text: {text}')
                tab_buttons.nth(i).click()
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                logger.info(f'Switched to tab {tab_name}.')
                found = True
                break
                
        if not found:
            logger.error(f'Could not find tab with name {tab_name}. Available tab buttons:')
            for i in range(tab_buttons.count()):
                logger.error(f'- {tab_buttons.nth(i).inner_text().strip()}')
            return False
            
        return True
        
    except Exception as e:
        logger.error(f'Could not switch to tab {tab_name}: {e}')
        return False

def convert_csv_to_xlsx(csv_path: str) -> Optional[str]:
    """Convert CSV file to XLSX format.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Path to the XLSX file if successful, None otherwise
    """
    try:
        xlsx_path = csv_path.replace('.csv', '.xlsx')
        df = pd.read_csv(csv_path)
        df.to_excel(xlsx_path, index=False)
        logger.info(f'Converted {csv_path} to {xlsx_path}')
        
        # Remove the original CSV file
        try:
            os.remove(csv_path)
            logger.info(f'Removed original CSV file: {csv_path}')
        except Exception as e:
            logger.warning(f'Failed to remove CSV file {csv_path}: {e}')
            
        return xlsx_path
    except Exception as e:
        logger.error(f'Failed to convert {csv_path} to XLSX: {e}')
        return None

def get_config() -> Dict[str, Any]:
    """Load scraper configuration from file.
    
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
        "date_filter": "Today", 
        "tabs": {tab["name"]: True for tab in TABS}
    }
    logger.info("Using default configuration")
    return default_config

def login_and_download_reports_for_user(username: str, password: str) -> bool:
    """Login and download reports for a specific user.
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            logger.info(f'\n==== Running for user: {username} ====')
            
            if not login(page, username, password):
                logger.error(f'Login failed for user: {username}')
                browser.close()
                return False
                
            if not navigate_to_reports(page):
                logger.error(f'Navigation to reports failed for user: {username}')
                browser.close()
                return False
                
            config = get_config()
            selected_filter = config.get('date_filter', 'Today')
            selected_tabs = config.get('tabs', {tab["name"]: True for tab in TABS})

            success_count = 0
            for tab in TABS:
                if not selected_tabs.get(tab["name"], True):
                    logger.info(f"\n--- Skipping {tab['name']} Report (not selected) ---")
                    continue
                    
                logger.info(f"\n--- Downloading {tab['name']} Report ---")
                if not switch_tab(page, tab['name']):
                    logger.error(f"Failed to switch to {tab['name']} tab")
                    continue
                    
                if download_report(page):
                    success_count += 1
                else:
                    logger.error(f"Failed to download {tab['name']} report")
                    
            browser.close()
            logger.info(f'Successfully downloaded {success_count} reports for user: {username}')
            return success_count > 0
            
    except Exception as e:
        logger.error(f'Error processing user {username}: {e}')
        return False

def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for the scraper.
    
    Args:
        argv: Command line arguments (optional)
    """
    parser = argparse.ArgumentParser(
        description='Learning A-Z Reports Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--users', 
        type=str, 
        default=USERS_FILE, 
        help=f'Path to users JSON file (default: {USERS_FILE})'
    )
    
    args = parser.parse_args(argv)
    
    logger.info(f'Starting scraper with users file: {args.users}')
    users = load_users(args.users)
    
    if not users:
        logger.error('No users found. Please check your users file.')
        return
    
    successful_users = 0
    for user in users:
        username = user.get('username')
        password = user.get('password')
        
        if not username or not password:
            logger.error(f'Invalid user data: {user}. Skipping...')
            continue
            
        logger.info(f'Processing user: {username}')
        if login_and_download_reports_for_user(username, password):
            successful_users += 1
        else:
            logger.error(f'Failed to process user: {username}')
    
    logger.info(f'Scraping completed. Processed {successful_users}/{len(users)} users successfully.')

if __name__ == '__main__':
    main()
