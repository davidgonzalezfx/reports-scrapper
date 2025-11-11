"""Central constants and configuration values for the reports scraper application.

This module contains all magic numbers, strings, and configuration constants
used throughout the application to improve maintainability and reduce duplication.
"""

from typing import List, Dict, Any

# ============================================================================
# File and Directory Paths
# ============================================================================

USERS_FILE: str = "users.json"
CONFIG_FILE: str = "scraper_config.json"
REPORTS_DIR: str = "reports"
LOG_FILE: str = "app.log"
SCRAPER_LOG_FILE: str = "scraper.log"


# ============================================================================
# URLs
# ============================================================================

LOGIN_URL: str = "https://accounts.learninga-z.com/ng/member/login?siteAbbr=rp"
RAZ_PLUS_URL: str = "https://www.raz-plus.com/"


# ============================================================================
# Timeouts (in milliseconds)
# ============================================================================

DEFAULT_TIMEOUT: int = 15000  # 15 seconds
LOGIN_TIMEOUT: int = 10000    # 10 seconds
DOWNLOAD_TIMEOUT: int = 30000  # 30 seconds
PAGE_LOAD_WAIT: int = 3        # seconds


# ============================================================================
# CSS Selectors
# ============================================================================

# Login page selectors
SELECTOR_USERNAME_INPUT: str = "input#username"
SELECTOR_PASSWORD_INPUT: str = "input#password"
SELECTOR_LOGIN_BUTTON: str = "button#memberLoginSubmitButton"
SELECTOR_LOGIN_BUTTON_ENABLED: str = "button#memberLoginSubmitButton:not([disabled])"

# Navigation selectors
SELECTOR_MENU_BUTTON: str = "span.buttonText"
SELECTOR_CLASSROOM_REPORTS: str = 'a:has-text("Classroom Reports")'
SELECTOR_CLASSROOM_GREETING: str = "h2.homepageGreeting.frazHomepageGreeting"

# Filter selectors
SELECTOR_DATE_FILTER: str = "#mat-select-0"
SELECTOR_PRODUCTS_FILTER: str = "#mat-select-2"
SELECTOR_FILTER_OPTION: str = "mat-option"

# Date input selectors
SELECTOR_START_DATE_INPUT: str = 'input[aria-label="Start date"]'
SELECTOR_END_DATE_INPUT: str = 'input[aria-label="End date"]'

# Report selectors
SELECTOR_REPORT_TAB: str = 'button[role="tab"]'
SELECTOR_ELLIPSIS_BUTTON: str = 'button[tid="class-reports-ellipsis-tooltip"]'
SELECTOR_CSV_DOWNLOAD: str = "#report-menu-options-0-csv-report-download-btn"
SELECTOR_NO_RESULTS: str = 'text="No results for filter criteria"'


# ============================================================================
# Report Types and Tabs
# ============================================================================

REPORT_TYPES: List[str] = [
    "Student Usage",
    "Skill",
    "Assignment",
    "Assessment",
    "Level Up Progress"
]

TABS: List[Dict[str, Any]] = [
    {"name": "Student Usage", "default": True},
    {"name": "Skill", "default": True},
    {"name": "Assignment", "default": True},
    {"name": "Assessment", "default": True},
    {"name": "Level Up Progress", "default": True},
]


# ============================================================================
# Filter Options
# ============================================================================

DATE_FILTERS: List[str] = [
    "Today",
    "Last 7 Days",
    "Last 30 Days",
    "Last 90 Days",
    "Last Year",
    "Custom"
]

PRODUCTS_FILTERS: List[str] = [
    "All",
    "Raz-Plus",
    "Español",
    "Science A-Z",
    "Writing A-Z",
    "Vocabulary A-Z",
    "Foundations A-Z"
]


# ============================================================================
# Excel Column Indices (0-based)
# ============================================================================

# Student Usage Report Columns
STUDENT_USAGE_COL_STUDENT_NAME: int = 0
STUDENT_USAGE_COL_CLASSROOM: int = 1
STUDENT_USAGE_COL_DISTRICT_ID: int = 2
STUDENT_USAGE_COL_GRADE: int = 3
STUDENT_USAGE_COL_TEACHER: int = 4
STUDENT_USAGE_COL_LISTEN: int = 5
STUDENT_USAGE_COL_READ: int = 6
STUDENT_USAGE_COL_QUIZ: int = 7
STUDENT_USAGE_COL_INTERACTIVITY: int = 8
STUDENT_USAGE_COL_PRACTICE_RECORDING: int = 9

# Skill Report Columns
SKILL_COL_SKILL_NAME: int = 0
SKILL_COL_CORRECT: int = 1
SKILL_COL_TOTAL: int = 2
SKILL_COL_ACCURACY: int = 3
SKILL_COL_DATA_BAR: int = 3  # Column D (0-indexed as 3) for data bars

# Level Up Progress Report Columns
LEVEL_UP_COL_STUDENT: int = 5
LEVEL_UP_COL_LEVEL: int = 6
LEVEL_UP_COL_PROGRESS: int = 7


# ============================================================================
# Excel Styling
# ============================================================================

# Header colors
EXCEL_HEADER_COLOR: str = "D4E6F1"  # Light blue
EXCEL_HEADER_FONT_COLOR: str = "000000"  # Black

# Data bar colors
EXCEL_DATA_BAR_COLOR: str = "4472C4"  # Blue

# Excel sheet name limits
EXCEL_MAX_SHEET_NAME_LENGTH: int = 31
EXCEL_INVALID_SHEET_CHARS: List[str] = [':', '\\', '/', '?', '*', '[', ']']

# Column width limits
EXCEL_MIN_COLUMN_WIDTH: int = 2
EXCEL_MAX_COLUMN_WIDTH: int = 50


# ============================================================================
# Spanish Month Names
# ============================================================================

SPANISH_MONTHS: Dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre"
}


# ============================================================================
# Date Ranges (in days)
# ============================================================================

DATE_RANGE_LAST_7_DAYS: int = 7
DATE_RANGE_LAST_30_DAYS: int = 30
DATE_RANGE_LAST_90_DAYS: int = 90
DATE_RANGE_LAST_YEAR: int = 365
DATE_RANGE_MAX_CUSTOM: int = 365  # Maximum allowed custom date range


# ============================================================================
# File Validation
# ============================================================================

DANGEROUS_FILENAME_PATTERNS: List[str] = ['..', '/', '\\']
ALLOWED_FILE_EXTENSIONS: List[str] = ['.xlsx', '.csv', '.json']


# ============================================================================
# Flask Configuration
# ============================================================================

FLASK_MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
DEFAULT_INSTITUTION_NAME: str = "Unidad Educativa"


# ============================================================================
# Browser Configuration
# ============================================================================

BROWSER_ARGS: List[str] = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--start-maximized'
]

BROWSER_USER_AGENT: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

BROWSER_VIEWPORT_WIDTH: int = 1280
BROWSER_VIEWPORT_HEIGHT: int = 1080


# ============================================================================
# Logging Configuration
# ============================================================================

LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'


# ============================================================================
# Report Filename Patterns
# ============================================================================

LEGACY_REPORT_PREFIXES: List[str] = [
    'Student Usage',
    'Skill',
    'Assignment',
    'Assessment',
    'Level Up Progress'
]

COMBINED_REPORT_PREFIX: str = "Combined_All_Reports_"
TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"


# ============================================================================
# Top Readers Configuration
# ============================================================================

TOP_READERS_COUNT: int = 3  # Number of top readers to show per classroom


# ============================================================================
# Summary Row Labels
# ============================================================================

SUMMARY_LABEL_TEACHERS: str = "Total Teachers"
SUMMARY_LABEL_STUDENTS: str = "Total Students"
SUMMARY_LABEL_LISTENS: str = "Total Listens"
SUMMARY_LABEL_READS: str = "Total Reads"
SUMMARY_LABEL_QUIZZES: str = "Total Quizzes"
SUMMARY_LABEL_TOTAL: str = "Total"
