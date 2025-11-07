"""Web scraper for educational reports using Playwright.

This module handles automated login and report downloading from an educational
platform using browser automation with Playwright.
"""

import argparse
import logging
import os
import sys
import time
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
    SELECTOR_MENU_BUTTON, SELECTOR_CLASSROOM_REPORTS,
    SELECTOR_DATE_FILTER, SELECTOR_PRODUCTS_FILTER, SELECTOR_FILTER_OPTION,
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
    """Navigate to the reports section of the platform.

    Args:
        page: Playwright page object

    Returns:
        True if navigation successful, False otherwise

    Raises:
        NavigationError: If navigation fails
    """
    try:
        logger.debug("Looking for Menu button")
        page.wait_for_selector(SELECTOR_MENU_BUTTON, timeout=DEFAULT_TIMEOUT)

        menu_buttons = page.locator(SELECTOR_MENU_BUTTON)
        menu_found = False

        for i in range(menu_buttons.count()):
            if menu_buttons.nth(i).inner_text().strip() == "Menu":
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
        page.wait_for_selector(
            SELECTOR_CLASSROOM_REPORTS,
            timeout=DEFAULT_TIMEOUT
        )
        page.click(SELECTOR_CLASSROOM_REPORTS)
        page.wait_for_load_state("networkidle")

        current_url = page.url
        logger.info(f"Successfully navigated to reports: {current_url}")
        time.sleep(PAGE_LOAD_WAIT)
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout while navigating to reports: {e}")
        return False
    except Exception as e:
        logger.error(f"Error navigating to reports: {e}")
        return False


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


def download_report(page: Page, username: str) -> bool:
    """Download the current report as CSV and convert to XLSX.

    Args:
        page: Playwright page object
        username: Username to include in filename

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

        # Click the options (ellipsis) button
        page.wait_for_selector(
            SELECTOR_ELLIPSIS_BUTTON,
            timeout=DEFAULT_TIMEOUT
        )
        page.click(SELECTOR_ELLIPSIS_BUTTON)
        time.sleep(1)

        # Download CSV
        logger.debug("Initiating CSV download")
        with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
            page.click(SELECTOR_CSV_DOWNLOAD)

        download = download_info.value
        original_filename = download.suggested_filename

        # Create user-specific filename
        user_filename = f"{username}_{original_filename}"

        reports_dir = get_reports_directory(REPORTS_DIR)
        csv_path = reports_dir / user_filename

        download.save_as(str(csv_path))
        logger.info(f"Downloaded CSV report: {user_filename}")

        # Convert CSV to XLSX
        if convert_csv_to_xlsx(str(csv_path)):
            return True
        else:
            return False

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
    config: Dict
) -> tuple[int, int]:
    """Process and download all selected report tabs for a user.

    Args:
        page: Playwright page object
        username: Username for the reports
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
                # Special handling for Level Up Progress
                if tab_name == "Level Up Progress":
                    products_filter = config.get("products_filter", "All")
                    if products_filter == "All":
                        select_products_filter(page, "Raz-Plus")
                    else:
                        select_products_filter(page, products_filter)

                if download_report(page, username):
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

                # Navigate back to Raz-Plus
                logger.debug("Navigating back to Raz-Plus main page")
                page.goto(RAZ_PLUS_URL)
                page.wait_for_load_state("networkidle")

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
