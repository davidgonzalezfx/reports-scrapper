import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import json

load_dotenv()

REPORTS_DIR = 'reports'
LOGIN_URL = 'https://accounts.learninga-z.com/ng/member/login?siteAbbr=rp'
USERNAME = os.getenv('SCRAPER_USERNAME', 'your_username')
PASSWORD = os.getenv('SCRAPER_PASSWORD', 'your_password')
CONFIG_FILE = 'scraper_config.json'

TABS = [
    {"name": "Student Usage" },
    {"name": "Skill" },
    {"name": "Assignment" },
    {"name": "Assessment" },
    {"name": "Level Up Progress" },
]

os.makedirs(REPORTS_DIR, exist_ok=True)

def login(page):
    print('Navigating to login page...')
    page.goto(LOGIN_URL)
    try:
        print('Filling in username...')
        page.fill('input#username', USERNAME)
        print('Filling in password...')
        page.fill('input#password', PASSWORD)
        print('Waiting for login button to be enabled...')
        page.wait_for_selector('button#memberLoginSubmitButton:not([disabled])', timeout=10000)
        print('Clicking login button...')
        page.click('button#memberLoginSubmitButton')
        page.wait_for_load_state('networkidle')
        print('After login, current URL:', page.url)
        if page.url.startswith(LOGIN_URL):
            print('Login failed: Still on login page.')
            return False
        print('Login successful!')
        return True
    except PlaywrightTimeoutError as e:
        print(f'Login failed due to timeout: {e}')
        return False

def navigate_to_reports(page):
    try:
        page.wait_for_selector('span.buttonText', timeout=15000)
        menu_buttons = page.locator('span.buttonText')
        for i in range(menu_buttons.count()):
            if menu_buttons.nth(i).inner_text().strip() == 'Menu':
                print('Clicking Menu button...')
                menu_buttons.nth(i).click()
                break
        time.sleep(2)
    except Exception as e:
        print('Could not find or click Menu button:', e)
        return False
    try:
        print('Looking for Classroom Reports link...')
        page.wait_for_selector('a:has-text("Classroom Reports")', timeout=15000)
        page.click('a:has-text("Classroom Reports")')
        page.wait_for_load_state('networkidle')
        print('Navigated to Classroom Reports. Current URL:', page.url)
        time.sleep(3)
        return True
    except Exception as e:
        print('Could not find or click Classroom Reports link:', e)
        return False

def select_date_filter(page, label):
    try:
        print(f'Selecting date filter: {label} ...')
        page.wait_for_selector('#mat-select-0', timeout=10000)
        page.click('#mat-select-0')
        time.sleep(1)
        page.wait_for_selector('mat-option .mat-option-text', timeout=10000)
        options = page.locator('mat-option .mat-option-text')
        for i in range(options.count()):
            if options.nth(i).inner_text().strip() == label:
                options.nth(i).click()
                print(f'Selected "{label}" in date filter.')
                break
        time.sleep(2)
    except Exception as e:
        print(f'Could not select date filter {label}:', e)
        return False
    return True

def download_report(page):
    try:
        # Check for 'No results for filter criteria' before attempting download
        if page.locator('text="No results for filter criteria"').count() > 0:
            print('No results for filter criteria. Skipping download for this tab.')
            return False
        print('Clicking options (ellipsis) button...')
        page.click('button[tid="class-reports-ellipsis-tooltip"]')
        time.sleep(1)
        print('Clicking download button and waiting for download...')
        with page.expect_download() as download_info:
            page.click('#report-menu-options-0-csv-report-download-btn')
        download = download_info.value
        filename = download.suggested_filename
        csv_path = os.path.join(REPORTS_DIR, filename)
        download.save_as(csv_path)
        print(f'Downloaded CSV to {csv_path}')
        convert_csv_to_xlsx(csv_path)
    except Exception as e:
        print('Failed to download report:', e)
        return False
    return True

def switch_tab(page, tab_name):
    try:
        print(f'Switching to tab: {tab_name}...')
        
        # Try by button text
        tab_buttons = page.locator('button[role="tab"]')
        found = False
        for i in range(tab_buttons.count()):
            text = tab_buttons.nth(i).inner_text().strip().lower()
            if tab_name.lower() in text:
                print(f'Clicking tab button with text: {text}')
                tab_buttons.nth(i).click()
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                print(f'Switched to tab {tab_name}.')
                found = True
                break
        if not found:
            print(f'Could not find tab with name {tab_name}. Available tab buttons:')
            for i in range(tab_buttons.count()):
                print('-', tab_buttons.nth(i).inner_text().strip())
            return False
        return True
    except Exception as e:
        print(f'Could not switch to tab {button_id} ({tab_name}):', e)
        return False

def convert_csv_to_xlsx(csv_path):
    xlsx_path = csv_path.replace('.csv', '.xlsx')
    df = pd.read_csv(csv_path)
    df.to_excel(xlsx_path, index=False)
    print(f'Converted {csv_path} to {xlsx_path}')

def get_selected_date_filter():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('date_filter', 'Today')
    return 'Today'

def login_and_download_reports():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        if not login(page):
            browser.close()
            return
        if not navigate_to_reports(page):
            browser.close()
            return
        # Student Usage tab (default, select date filter from config)
        selected_filter = get_selected_date_filter()
        print(f'\n--- Downloading Student Usage Report with date filter: {selected_filter} ---')
        select_date_filter(page, selected_filter)
        download_report(page)
        # Other tabs
        for tab in TABS[1:]:
            print(f"\n--- Downloading {tab['name']} Report ---")
            if not switch_tab(page, tab['name']):
                continue
            download_report(page)
        browser.close()

def main():
    login_and_download_reports()

if __name__ == '__main__':
    main() 
