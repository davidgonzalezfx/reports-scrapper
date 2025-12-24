"""Web scraper for educational reports using Playwright.

This module handles automated login and report downloading from an educational
platform using browser automation with Playwright.
"""

import argparse
import logging
import os
import sys
import time
import zipfile
from typing import List, Dict, Optional

import pandas as pd
from dotenv import load_dotenv

# IMPORTANT: Set up Playwright environment BEFORE importing playwright
# This must happen before any playwright imports to ensure the browser
# is found in the local playwright-browsers directory
from path_helpers import (
    setup_playwright_environment, get_reports_directory, is_frozen
)

# Set up the environment variable for Playwright browsers location
setup_playwright_environment()

# Now we can safely import Playwright
from playwright.sync_api import (
    sync_playwright, Page, Browser, BrowserContext,
    TimeoutError as PlaywrightTimeoutError
)

# Import other helper modules
from constants import (
    REPORTS_DIR, LOGIN_URL, RAZ_PLUS_URL, CONFIG_FILE, USERS_FILE,
    DEFAULT_TIMEOUT, LOGIN_TIMEOUT, DOWNLOAD_TIMEOUT, PAGE_LOAD_WAIT,
    SELECTOR_USERNAME_INPUT, SELECTOR_PASSWORD_INPUT,
    SELECTOR_LOGIN_BUTTON_ENABLED, SELECTOR_LOGIN_BUTTON,
    SELECTOR_ADMIN_REPORTS,
    SELECTOR_CLASSROOM_GREETING,
    SELECTOR_DATE_FILTER, SELECTOR_PRODUCTS_FILTER, SELECTOR_SKILL_FILTER,
    SELECTOR_LANGUAGE_FILTER, SELECTOR_STATUS_FILTER, SELECTOR_FILTER_OPTION,
    SELECTOR_AGGREGATE_SKILL_SKILL, SELECTOR_AGGREGATE_SKILL_SCHOOL,
    SELECTOR_AGGREGATE_SKILL_TEACHER, SELECTOR_AGGREGATE_SKILL_SELECTED,
    SELECTOR_START_DATE_INPUT, SELECTOR_END_DATE_INPUT,
    SELECTOR_REPORT_TAB, SELECTOR_ELLIPSIS_BUTTON, SELECTOR_CSV_DOWNLOAD,
    SELECTOR_NO_RESULTS, TABS, BROWSER_ARGS, BROWSER_USER_AGENT,
    BROWSER_VIEWPORT_WIDTH, BROWSER_VIEWPORT_HEIGHT
)
from config import load_config as load_scraper_config
from models import UserResult, ScraperResult
from date_helpers import convert_date_for_website
from logging_config import setup_scraper_logging, get_logger
from exceptions import (
    LoginError, NavigationError, ProductAccessError,
    DownloadError, TabSwitchError, BrowserError
)
from utils import load_json, convert_csv_to_xlsx

# Load environment variables
load_dotenv()

# Setup logging
setup_scraper_logging()
logger = get_logger(__name__)

# Environment defaults
USERNAME = os.getenv("SCRAPER_USERNAME", "your_username")
PASSWORD = os.getenv("SCRAPER_PASSWORD", "your_password")

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)


def load_users(users_file: str = USERS_FILE) -> List[Dict[str, str]]:
    """Load users from JSON file.

    Args:
        users_file: Path to users JSON file

    Returns:
        List of user dictionaries with username and password
    """
    users = load_json(users_file, [])
    logger.info(f"Loaded {len(users)} users from {users_file}")
    return users


def login(page: Page, username: str, password: str) -> bool:
    """Perform login to the educational platform.

    Args:
        page: Playwright page object
        username: User's login username
        password: User's login password

    Returns:
        True if login successful, False otherwise

    Raises:
        LoginError: If login fails
    """
    try:
        logger.info(f"Attempting login for user: {username}")
        logger.debug("Navigating to login page")
        page.goto(LOGIN_URL)

        logger.debug("Filling in credentials")
        page.fill(SELECTOR_USERNAME_INPUT, username)
        page.fill(SELECTOR_PASSWORD_INPUT, password)

        logger.debug("Waiting for login button to be enabled")
        page.wait_for_selector(
            SELECTOR_LOGIN_BUTTON_ENABLED,
            timeout=LOGIN_TIMEOUT
        )

        logger.debug("Clicking login button")
        page.click(SELECTOR_LOGIN_BUTTON)
        page.wait_for_load_state("networkidle")

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


def navigate_to_reports(page: Page) -> bool:
    """Navigate to the admin reports section of the platform.

    Args:
        page: Playwright page object

    Returns:
        True if navigation successful, False otherwise

    Raises:
        NavigationError: If navigation fails
    """
    try:
        logger.debug("Looking for Reports link")
        page.wait_for_selector(
            SELECTOR_ADMIN_REPORTS,
            timeout=DEFAULT_TIMEOUT
        )
        page.click(SELECTOR_ADMIN_REPORTS)
        page.wait_for_load_state("networkidle")

        current_url = page.url
        logger.info(f"Successfully navigated to admin reports: {current_url}")
        time.sleep(PAGE_LOAD_WAIT)
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout while navigating to admin reports: {e}")
        return False
    except Exception as e:
        logger.error(f"Error navigating to admin reports: {e}")
        return False


def extract_classroom_name(page: Page) -> Optional[str]:
    """Extract classroom name from homepage greeting.

    Args:
        page: Playwright page object

    Returns:
        Classroom name (e.g., "1A Josefa Andrea") or None if not found
    """
    try:
        logger.debug("Attempting to extract classroom name from greeting")

        # Look for the greeting element
        greeting_locator = page.locator(SELECTOR_CLASSROOM_GREETING)
        if greeting_locator.count() > 0:
            greeting_text = greeting_locator.first.inner_text().strip()
            logger.debug(f"Found greeting text: {greeting_text}")

            # Remove "Hi " prefix if present
            if greeting_text.startswith("Hi "):
                classroom_name = greeting_text[3:].strip()
                logger.info(f"Extracted classroom name: {classroom_name}")
                return classroom_name[:-1]  # Remove trailing punctuation if any
            else:
                # If no "Hi " prefix, return the text as-is
                logger.info(f"Extracted classroom name: {greeting_text}")
                return greeting_text

        logger.warning("Could not find classroom greeting element")
        return None

    except Exception as e:
        logger.error(f"Error extracting classroom name: {e}")
        return None


def select_date_filter(
    page: Page,
    label: str,
    custom_start_date: Optional[str] = None,
    custom_end_date: Optional[str] = None
) -> bool:
    """Select a date filter option from the dropdown.

    Args:
        page: Playwright page object
        label: Date filter label to select
        custom_start_date: Custom start date in DD/MM/YYYY format
        custom_end_date: Custom end date in DD/MM/YYYY format

    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.debug(f"Selecting date filter: {label}")

        # Click on the date filter dropdown
        page.wait_for_selector(SELECTOR_DATE_FILTER, timeout=DEFAULT_TIMEOUT)
        page.click(SELECTOR_DATE_FILTER)
        time.sleep(1)

        # Wait for options and select
        page.wait_for_selector(SELECTOR_FILTER_OPTION, timeout=DEFAULT_TIMEOUT)
        options = page.locator(SELECTOR_FILTER_OPTION)

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

        # Handle custom dates if "Custom" is selected
        if label == "Custom" and custom_start_date and custom_end_date:
            logger.debug(
                f"Setting custom date range: {custom_start_date} "
                f"to {custom_end_date}"
            )
            time.sleep(2)  # Wait for custom date inputs

            try:
                # Convert dates to website format (MM/DD/YYYY)
                start_date_website = convert_date_for_website(custom_start_date)
                end_date_website = convert_date_for_website(custom_end_date)

                if not start_date_website or not end_date_website:
                    logger.error("Failed to convert custom dates")
                    return False

                # Fill start date
                page.wait_for_selector(
                    SELECTOR_START_DATE_INPUT,
                    timeout=DEFAULT_TIMEOUT
                )
                page.fill(SELECTOR_START_DATE_INPUT, start_date_website)
                logger.debug(f"Filled start date: {start_date_website}")

                # Fill end date
                page.wait_for_selector(
                    SELECTOR_END_DATE_INPUT,
                    timeout=DEFAULT_TIMEOUT
                )
                page.fill(SELECTOR_END_DATE_INPUT, end_date_website)
                logger.debug(f"Filled end date: {end_date_website}")

                time.sleep(1)

            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout filling custom date fields: {e}")
                return False

        time.sleep(2)  # Allow filter to apply
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting date filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting date filter '{label}': {e}")
        return False


def select_products_filter(
    page: Page,
    label: str,
    stop_on_error: bool = True
) -> bool:
    """Select a products filter option from the dropdown.

    Args:
        page: Playwright page object
        label: Products filter label to select
        stop_on_error: If True, raise exception when product not found

    Returns:
        True if selection successful, False otherwise

    Raises:
        ProductAccessError: When product not available and stop_on_error is True
    """
    try:
        logger.debug(f"Selecting products filter: {label}")

        # Click on the products filter dropdown
        page.wait_for_selector(
            SELECTOR_PRODUCTS_FILTER,
            timeout=DEFAULT_TIMEOUT
        )
        page.click(SELECTOR_PRODUCTS_FILTER)
        time.sleep(1)

        # Wait for options and select
        page.wait_for_selector(SELECTOR_FILTER_OPTION, timeout=DEFAULT_TIMEOUT)
        options = page.locator(SELECTOR_FILTER_OPTION)

        option_found = False
        for i in range(options.count()):
            option_text = options.nth(i).inner_text().strip()
            if option_text == label:
                options.nth(i).click()
                logger.info(f"Selected products filter: {label}")
                option_found = True
                break

        if not option_found:
            error_msg = (
                f"Products filter option '{label}' not found - "
                f"user may not have access to this product"
            )
            logger.error(error_msg)
            if stop_on_error and label != "All":
                raise ProductAccessError(label, "unknown", error_msg)
            return False

        time.sleep(2)  # Allow filter to apply
        return True

    except ProductAccessError:
        raise  # Re-raise custom exception
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting products filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting products filter '{label}': {e}")
        return False


def select_skill_filter(page: Page, label: str) -> bool:
    """Select a skill filter option from the dropdown.

    Args:
        page: Playwright page object
        label: Skill filter label to select

    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.debug(f"Selecting skill filter: {label}")

        # Click on the skill filter dropdown
        page.wait_for_selector(SELECTOR_SKILL_FILTER, timeout=DEFAULT_TIMEOUT)
        page.click(SELECTOR_SKILL_FILTER)
        time.sleep(1)

        # Wait for options and select
        page.wait_for_selector(SELECTOR_FILTER_OPTION, timeout=DEFAULT_TIMEOUT)
        options = page.locator(SELECTOR_FILTER_OPTION)

        for i in range(options.count()):
            option_text = options.nth(i).inner_text().strip()
            if option_text == label:
                options.nth(i).click()
                logger.info(f"Selected skill filter: {label}")
                time.sleep(2)  # Allow filter to apply
                return True

        logger.warning(f"Skill filter option '{label}' not found")
        return False

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting skill filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting skill filter '{label}': {e}")
        return False


def select_aggregate_skill_by_filter(page: Page, aggregate_by: str) -> bool:
    """Select the aggregate by option for skills report.

    Args:
        page: Playwright page object
        aggregate_by: One of 'skill', 'school', 'teacher'

    Returns:
        True if selection successful, False otherwise
    """
    try:
        # Map filter value to CSS selector
        selector_map = {
            "skill": SELECTOR_AGGREGATE_SKILL_SKILL,
            "school": SELECTOR_AGGREGATE_SKILL_SCHOOL,
            "teacher": SELECTOR_AGGREGATE_SKILL_TEACHER
        }

        if aggregate_by not in selector_map:
            logger.error(f"Invalid aggregate_by value: {aggregate_by}")
            return False

        selector = selector_map[aggregate_by]
        logger.debug(f"Selecting aggregate by: {aggregate_by}")

        # Check if already selected
        try:
            selected_button = page.locator(SELECTOR_AGGREGATE_SKILL_SELECTED)
            if selected_button.count() > 0:
                current_text = selected_button.inner_text().strip().lower()
                if current_text == aggregate_by:
                    logger.info(f"Aggregate by '{aggregate_by}' already selected")
                    return True
        except Exception:
            pass  # Continue to click

        # Wait for and click the appropriate button
        page.wait_for_selector(selector, timeout=DEFAULT_TIMEOUT)
        page.click(selector)
        time.sleep(2)  # Allow filter to apply

        logger.info(f"Selected aggregate by: {aggregate_by}")
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting aggregate by '{aggregate_by}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting aggregate by '{aggregate_by}': {e}")
        return False


def select_language_filter(page: Page, label: str) -> bool:
    """Select a language filter option from the dropdown.

    Args:
        page: Playwright page object
        label: Language filter label to select

    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.debug(f"Selecting language filter: {label}")

        # Click on the language filter dropdown
        page.wait_for_selector(SELECTOR_LANGUAGE_FILTER, timeout=DEFAULT_TIMEOUT)
        page.click(SELECTOR_LANGUAGE_FILTER)
        time.sleep(1)

        # Wait for options and select
        page.wait_for_selector(SELECTOR_FILTER_OPTION, timeout=DEFAULT_TIMEOUT)
        options = page.locator(SELECTOR_FILTER_OPTION)

        for i in range(options.count()):
            option_text = options.nth(i).inner_text().strip()
            if option_text == label:
                options.nth(i).click()
                logger.info(f"Selected language filter: {label}")
                time.sleep(2)  # Allow filter to apply
                return True

        logger.warning(f"Language filter option '{label}' not found")
        return False

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting language filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting language filter '{label}': {e}")
        return False


def select_status_filter(page: Page, label: str) -> bool:
    """Select a status filter option from the dropdown.

    Args:
        page: Playwright page object
        label: Status filter label to select

    Returns:
        True if selection successful, False otherwise
    """
    try:
        logger.debug(f"Selecting status filter: {label}")

        # Click on the status filter dropdown
        page.wait_for_selector(SELECTOR_STATUS_FILTER, timeout=DEFAULT_TIMEOUT)
        page.click(SELECTOR_STATUS_FILTER)
        time.sleep(1)

        # Wait for options and select
        page.wait_for_selector(SELECTOR_FILTER_OPTION, timeout=DEFAULT_TIMEOUT)
        options = page.locator(SELECTOR_FILTER_OPTION)

        for i in range(options.count()):
            option_text = options.nth(i).inner_text().strip()
            if option_text == label:
                options.nth(i).click()
                logger.info(f"Selected status filter: {label}")
                time.sleep(2)  # Allow filter to apply
                return True

        logger.warning(f"Status filter option '{label}' not found")
        return False

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout selecting status filter '{label}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error selecting status filter '{label}': {e}")
        return False


def extract_csv_from_zip(zip_path: str, reports_dir: str, classroom_name: str) -> List[str]:
    """Extract CSV files from ZIP and return paths to all extracted CSVs.

    Args:
        zip_path: Path to the downloaded ZIP file
        reports_dir: Directory where reports are stored
        classroom_name: Classroom name for filename

    Returns:
        List of paths to extracted CSV files, or empty list if extraction failed
    """
    try:
        logger.debug(f"Extracting CSV from ZIP: {zip_path}")

        # Create extraction directory
        extract_dir = os.path.join(reports_dir, f"{classroom_name}_extracted")
        os.makedirs(extract_dir, exist_ok=True)

        extracted_csv_files = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(extract_dir)

            # Find CSV files in the extracted content
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith('.csv'):
                        # Skip Student Usage and Teacher Usage files
                        if 'student usage' in file.lower() or 'teacher usage' in file.lower():
                            logger.info(f"Skipping {file} (filtered out)")
                            continue

                        extracted_csv_path = os.path.join(root, file)
                        # Rename to include classroom name
                        new_csv_name = f"{classroom_name}_{file}"
                        new_csv_path = os.path.join(reports_dir, new_csv_name)
                        os.rename(extracted_csv_path, new_csv_path)
                        extracted_csv_files.append(new_csv_path)
                        logger.info(f"Extracted CSV: {new_csv_name}")

        # Clean up extraction directory if empty
        try:
            if os.listdir(extract_dir):
                os.rmdir(extract_dir)
        except OSError:
            pass  # Directory not empty, leave it

        # Remove the original ZIP file
        os.remove(zip_path)
        logger.debug(f"Removed original ZIP file: {zip_path}")

        # Return all extracted CSV files
        return extracted_csv_files if extracted_csv_files else []

    except Exception as e:
        logger.error(f"Error extracting CSV from ZIP: {e}")
        return None


def download_report(page: Page, username: str, classroom_name: str) -> bool:
    """Download the current report as CSV/ZIP and convert to XLSX.

    Args:
        page: Playwright page object
        username: Username (for logging purposes)
        classroom_name: Classroom name to include in filename

    Returns:
        True if download successful, False otherwise
    """
    try:
        # Check if there are any results
        no_results_locator = page.locator(SELECTOR_NO_RESULTS)
        if no_results_locator.count() > 0:
            logger.warning("No results for filter criteria, skipping download")
            return False

        logger.debug("Attempting to download report")

        # wait tab to load its data
        page.wait_for_load_state("networkidle")

        # Click the options (ellipsis) button
        page.wait_for_selector(
            SELECTOR_ELLIPSIS_BUTTON,
            timeout=DEFAULT_TIMEOUT
        )
        page.click(SELECTOR_ELLIPSIS_BUTTON)
        time.sleep(1)

        # Download file
        logger.debug("Initiating download")

        with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
            page.click(SELECTOR_CSV_DOWNLOAD)

        download = download_info.value
        original_filename = download.suggested_filename

        # Create classroom-specific filename
        classroom_filename = f"{classroom_name}_{original_filename}"

        reports_dir = get_reports_directory(REPORTS_DIR)
        file_path = reports_dir / classroom_filename

        download.save_as(str(file_path))

        # Determine file type from extension
        file_extension = original_filename.lower().split('.')[-1] if '.' in original_filename else original_filename[-3:]
        file_type = file_extension.upper()
        logger.info(f"Downloaded {file_type} report: {classroom_filename}")

        # Handle ZIP extraction
        if file_extension == 'zip':
            extracted_files = extract_csv_from_zip(str(file_path), str(reports_dir), classroom_name)
            if not extracted_files or len(extracted_files) == 0:
                logger.error("Failed to extract CSV from ZIP file")
                return False

            # Convert all extracted CSV files to XLSX
            successful_conversions = 0
            for csv_path in extracted_files:
                if convert_csv_to_xlsx(csv_path):
                    successful_conversions += 1
                    logger.debug(f"Successfully converted {os.path.basename(csv_path)} to XLSX")
                else:
                    logger.warning(f"Failed to convert {os.path.basename(csv_path)} to XLSX")

            logger.info(f"Converted {successful_conversions}/{len(extracted_files)} CSV files to XLSX")
            return successful_conversions > 0
        else:
            # Convert CSV to XLSX
            return convert_csv_to_xlsx(str(file_path))

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout during report download: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        return False


def switch_tab(page: Page, tab_name: str) -> bool:
    """Switch to a specific report tab.

    Args:
        page: Playwright page object
        tab_name: Name of the tab to switch to

    Returns:
        True if tab switch successful, False otherwise
    """
    try:
        logger.debug(f"Switching to tab: {tab_name}")

        tab_buttons = page.locator(SELECTOR_REPORT_TAB)
        tab_found = False
        available_tabs = []

        for i in range(tab_buttons.count()):
            button_text = tab_buttons.nth(i).inner_text().strip()
            available_tabs.append(button_text)

            if tab_name.lower() in button_text.lower():
                logger.debug(f"Clicking tab button: {button_text}")
                tab_buttons.nth(i).click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)  # Allow tab content to load
                logger.info(f"Successfully switched to tab: {tab_name}")
                tab_found = True
                break

        if not tab_found:
            logger.error(
                f"Tab '{tab_name}' not found. Available tabs: {available_tabs}"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Error switching to tab '{tab_name}': {e}")
        return False


def create_browser_context(browser: Browser) -> BrowserContext:
    """Create a browser context with proper configuration.

    Args:
        browser: Browser instance

    Returns:
        Configured BrowserContext
    """
    return browser.new_context(
        accept_downloads=True,
        user_agent=BROWSER_USER_AGENT,
        viewport={
            "width": BROWSER_VIEWPORT_WIDTH,
            "height": BROWSER_VIEWPORT_HEIGHT
        },
        ignore_https_errors=True
    )


def process_user_reports(
    page: Page,
    username: str,
    classroom_name: str,
    config: Dict
) -> tuple[int, int]:
    """Process and download all selected report tabs for a user.

    Args:
        page: Playwright page object
        username: Username for the reports
        classroom_name: Classroom name to use in filenames
        config: Scraper configuration dictionary

    Returns:
        Tuple of (successful_downloads, total_tabs_attempted)
    """
    selected_tabs = config.get("tabs", {})
    successful_downloads = 0
    total_tabs = sum(
        1 for tab in TABS
        if selected_tabs.get(tab["name"], True)
    )

    for tab in TABS:
        tab_name = tab["name"]

        if not selected_tabs.get(tab_name, True):
            logger.info(f"Skipping {tab_name} report (not selected)")
            continue

        logger.info(f"Processing {tab_name} report")

        try:
            if switch_tab(page, tab_name):
                # Apply skill filter for Student Skills tab
                if tab_name == "Student Skills":
                    skill_filter = config.get("skill_filter", "All")
                    if not select_skill_filter(page, skill_filter):
                        logger.warning(
                            f"Failed to apply skill filter '{skill_filter}'"
                        )

                    # Apply aggregate by filter
                    aggregate_by = config.get("aggregate_skill_by_filter", "skill")
                    if not select_aggregate_skill_by_filter(page, aggregate_by):
                        logger.warning(
                            f"Failed to apply aggregate by filter '{aggregate_by}'"
                        )

                # Apply language and status filters for Teacher Usage tab
                if tab_name == "Teacher Usage":
                    language_filter = config.get("language_filter", "All")
                    if not select_language_filter(page, language_filter):
                        logger.warning(
                            f"Failed to apply language filter '{language_filter}'"
                        )

                    status_filter = config.get("status_filter", "All")
                    if not select_status_filter(page, status_filter):
                        logger.warning(
                            f"Failed to apply status filter '{status_filter}'"
                        )

                if download_report(page, username, classroom_name):
                    successful_downloads += 1
                    logger.info(f"Successfully downloaded {tab_name} report")
                else:
                    logger.warning(f"Failed to download {tab_name} report")
            else:
                logger.warning(f"Failed to switch to {tab_name} tab")

        except Exception as e:
            logger.error(f"Error processing {tab_name} report: {e}")

    return successful_downloads, total_tabs


def login_and_download_reports_for_user(
    username: str,
    password: str
) -> UserResult:
    """Login and download reports for a specific user.

    Args:
        username: User's login username
        password: User's login password

    Returns:
        UserResult object with details about the processing
    """
    logger.info(f"Starting report download process for user: {username}")

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS
            )

            context = create_browser_context(browser)
            page = context.new_page()

            try:
                # Perform login
                if not login(page, username, password):
                    logger.error(f"Login failed for user: {username}")
                    return UserResult(
                        username=username,
                        success=False,
                        error="Failed to login - please check credentials",
                        error_type="login"
                    )

                # Extract classroom name from homepage
                classroom_name = extract_classroom_name(page)
                if not classroom_name:
                    logger.warning(
                        f"Could not extract classroom name for {username}, "
                        f"using username instead"
                    )
                    classroom_name = username
                else:
                    logger.info(
                        f"Using classroom name '{classroom_name}' for {username}"
                    )

                # Navigate to reports section
                if not navigate_to_reports(page):
                    logger.error(
                        f"Failed to navigate to reports for user: {username}"
                    )
                    return UserResult(
                        username=username,
                        success=False,
                        error="Failed to navigate to reports section",
                        error_type="navigation"
                    )

                # Load configuration
                config = load_scraper_config()
                selected_date_filter = config.date_filter
                selected_products_filter = config.products_filter

                logger.info(f"Using date filter: {selected_date_filter}")
                logger.info(f"Using products filter: {selected_products_filter}")

                # Apply products filter
                try:
                    if not select_products_filter(page, selected_products_filter):
                        logger.warning(
                            f"Failed to set products filter to "
                            f"'{selected_products_filter}' - continuing with default"
                        )
                except ProductAccessError as e:
                    logger.error(f"Product filter error for user {username}: {e}")
                    error_msg = str(e)
                    if "not found" in error_msg:
                        error_msg = (
                            f"Product '{selected_products_filter}' not available - "
                            f"user may not have access to this product"
                        )
                    return UserResult(
                        username=username,
                        success=False,
                        error=error_msg,
                        error_type="product_access"
                    )

                # Apply date filter
                custom_start = config.custom_start_date
                custom_end = config.custom_end_date

                if not select_date_filter(
                    page,
                    selected_date_filter,
                    custom_start,
                    custom_end
                ):
                    logger.warning(
                        f"Failed to set date filter to '{selected_date_filter}', "
                        f"continuing with current filter"
                    )

                # Process all tabs
                successful_downloads, total_tabs = process_user_reports(
                    page,
                    username,
                    classroom_name,
                    config.to_dict()
                )

                logger.info(
                    f"Completed report download for {username}: "
                    f"{successful_downloads}/{total_tabs} successful"
                )

                if successful_downloads == 0:
                    return UserResult(
                        username=username,
                        success=False,
                        error=(
                            f"No reports could be downloaded "
                            f"(0/{total_tabs} successful)"
                        ),
                        error_type="download",
                        reports_downloaded=successful_downloads,
                        reports_attempted=total_tabs
                    )

                return UserResult(
                    username=username,
                    success=True,
                    reports_downloaded=successful_downloads,
                    reports_attempted=total_tabs
                )

            finally:
                browser.close()

    except Exception as e:
        logger.error(
            f"Unexpected error during report download for {username}: {e}"
        )
        return UserResult(
            username=username,
            success=False,
            error=f"Unexpected error: {str(e)}",
            error_type="unexpected"
        )


def run_scraper_for_users(
    users_file: str = USERS_FILE,
    verbose: bool = False
) -> ScraperResult:
    """Run the scraper for all users in the users file.

    Args:
        users_file: Path to users JSON file
        verbose: Enable verbose logging

    Returns:
        ScraperResult object with details about the entire operation
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
        return ScraperResult(
            success=False,
            users_processed=0,
            total_users=0,
            warnings=["No users found in configuration file"]
        )

    logger.info(f"Found {len(users)} users to process")

    # Initialize result object
    result = ScraperResult(
        success=False,
        users_processed=0,
        total_users=len(users),
        user_results=[],
        warnings=[]
    )

    # Process each user
    for i, user in enumerate(users, 1):
        username = user.get("username")
        password = user.get("password")

        if not username or not password:
            logger.error(f"User {i}: Missing username or password, skipping")
            result.warnings.append(f"User {i}: Missing credentials, skipped")
            continue

        logger.info(f"Processing user {i}/{len(users)}: {username}")

        try:
            user_result = login_and_download_reports_for_user(
                username,
                password
            )
            result.user_results.append(user_result)

            if user_result.success:
                result.users_processed += 1
                logger.info(f"Successfully processed user: {username}")
            else:
                logger.error(
                    f"Failed to process user: {username} - {user_result.error}"
                )

        except Exception as e:
            logger.error(f"Unexpected error processing user {username}: {e}")
            result.user_results.append(UserResult(
                username=username,
                success=False,
                error=f"Unexpected error: {str(e)}",
                error_type="unexpected"
            ))

    # Set overall success based on whether any users were processed
    result.success = result.users_processed > 0

    logger.info(
        f"Scraper completed: {result.users_processed}/"
        f"{result.total_users} users processed successfully"
    )

    # Log error summary if there were failures
    if not result.success or result.users_processed < result.total_users:
        error_summary = result.get_error_summary()
        logger.info(f"Error summary: {error_summary}")

    # Combine all reports if scraping was successful
    if result.success:
        logger.info("Attempting to combine all reports by type...")
        try:
            from utils import combine_all_reports
            combined_file = combine_all_reports(REPORTS_DIR)
            if combined_file:
                logger.info(
                    f"Successfully created combined reports: {combined_file}"
                )
                result.warnings.append(
                    f"Combined reports saved to: {os.path.basename(combined_file)}"
                )
            else:
                logger.info("No reports to combine or combination failed")
        except Exception as e:
            logger.error(f"Error combining reports: {e}")
            result.warnings.append(f"Failed to combine reports: {str(e)}")

    return result


def main() -> None:
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Educational platform report scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--users",
        type=str,
        default=USERS_FILE,
        help="Path to users JSON file containing login credentials"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=CONFIG_FILE,
        help="Path to scraper configuration file"
    )

    args = parser.parse_args()

    # Run the scraper
    result = run_scraper_for_users(args.users, args.verbose)

    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        raise
