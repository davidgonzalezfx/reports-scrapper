"""Flask web application for reports scraping management.

This module provides a web interface for managing and executing the educational
platform report scraper. It handles user configuration, report downloads,
and presentation of aggregated data.
"""

import os
import threading
import time
import webbrowser
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import (
    Flask, render_template, send_from_directory, redirect,
    url_for, request, jsonify
)
from waitress import serve

# Import new helper modules
from constants import (
    USERS_FILE, REPORTS_DIR, DATE_FILTERS, PRODUCTS_FILTERS, SKILL_FILTERS,
    AGGREGATE_SKILL_BY_FILTERS, LANGUAGE_FILTERS, STATUS_FILTERS,
    TABS, FLASK_MAX_CONTENT_LENGTH, LEGACY_REPORT_PREFIXES,
    COMBINED_REPORT_PREFIX
)
from config import load_config, save_config, ScraperConfig
from models import (
    FileInfo, CombinedReportInfo, NotificationMessage
)
from date_helpers import (
    get_date_range_string, get_subtitle_string,
    format_date_for_html_input, format_date_for_storage,
    validate_date_range
)
from path_helpers import get_reports_directory, get_log_file_path, is_frozen
from logging_config import setup_app_logging, clear_log_file, get_logger
from exceptions import ConfigurationError, ValidationError, FileOperationError
from utils import (
    load_json, save_json, validate_filename, validate_user_data,
    get_report_files, get_school_summary, get_teacher_summaries,
    get_skills_summary, get_overall_skills_table,
    get_top_readers_per_classroom, get_level_up_progress_data,
    get_teacher_comparison_data, get_assignment_data, get_assessment_data,
    get_teacher_usage_summaries
)

# Setup logging
setup_app_logging()
logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = FLASK_MAX_CONTENT_LENGTH


# Custom Jinja2 filters for skills filtering
def filter_non_standard_skills(skills_list):
    """Filter out skills starting with RI or RL (reading standards).

    Args:
        skills_list: List of skill dictionaries

    Returns:
        List of skills not starting with RI or RL
    """
    if not skills_list:
        return []
    return [s for s in skills_list if not s["name"].startswith(("RI.", "RL."))]


def filter_standard_skills(skills_list):
    """Filter only skills starting with RI or RL (reading standards).

    Args:
        skills_list: List of skill dictionaries

    Returns:
        List of skills starting with RI or RL
    """
    if not skills_list:
        return []
    return [s for s in skills_list if s["name"].startswith(("RI.", "RL."))]


# Register custom filters with Jinja2
app.jinja_env.filters["non_standard_skills"] = filter_non_standard_skills
app.jinja_env.filters["standard_skills"] = filter_standard_skills


class AppState:
    """Thread-safe application state management."""

    def __init__(self) -> None:
        """Initialize application state."""
        self.download_in_progress: bool = False
        self._lock: threading.Lock = threading.Lock()
        self.notifications: List[Dict[str, str]] = []

    def set_download_status(self, status: bool) -> None:
        """Set download status in a thread-safe manner.

        Args:
            status: Whether download is in progress
        """
        with self._lock:
            self.download_in_progress = status

    def get_download_status(self) -> bool:
        """Get current download status in a thread-safe manner.

        Returns:
            True if download is in progress, False otherwise
        """
        with self._lock:
            return self.download_in_progress

    def add_notification(
        self,
        message: str,
        notification_type: str = "warning"
    ) -> None:
        """Add a notification in a thread-safe manner.

        Args:
            message: Notification message
            notification_type: Type of notification (info, warning, error, success)
        """
        with self._lock:
            notification = NotificationMessage.create(message, notification_type)
            self.notifications.append({
                "message": notification.message,
                "type": notification.type,
                "timestamp": notification.timestamp
            })
            logger.info(f"Added notification: {notification_type} - {message}")

    def get_notifications(self) -> List[Dict[str, str]]:
        """Get all notifications in a thread-safe manner.

        Returns:
            Copy of notifications list
        """
        with self._lock:
            return self.notifications.copy()

    def clear_notifications(self) -> None:
        """Clear all notifications in a thread-safe manner."""
        with self._lock:
            self.notifications = []
            logger.info("Cleared all notifications")


app_state = AppState()


def load_users() -> List[Dict[str, str]]:
    """Load users from file with fallback to empty list.

    Returns:
        List of user dictionaries with username and password
    """
    users = load_json(USERS_FILE, [])
    logger.info(f"Loaded {len(users)} users successfully")
    return users


def save_users(users: List[Dict[str, str]]) -> None:
    """Save users to file.

    Args:
        users: List of user dictionaries

    Raises:
        FileOperationError: If save fails
    """
    if not save_json(users, USERS_FILE):
        raise FileOperationError("save", USERS_FILE)
    logger.info(f"Saved {len(users)} users successfully")


def parse_file_info(filename: str) -> FileInfo:
    """Parse user and report information from filename.

    Expected format: username_originalfilename.xlsx

    Args:
        filename: Filename to parse

    Returns:
        FileInfo object with parsed information
    """
    try:
        name_without_ext = filename.rsplit(".", 1)[0]
        parts = name_without_ext.split("_", 1)

        if len(parts) == 2:
            username, report_name = parts

            # Check if this is a legacy file
            if any(name_without_ext.startswith(prefix)
                   for prefix in LEGACY_REPORT_PREFIXES):
                return FileInfo(
                    filename=filename,
                    user="Unknown",
                    report_name=name_without_ext
                )

            return FileInfo(
                filename=filename,
                user=username,
                report_name=report_name
            )

        # Single part or no underscore - treat as legacy
        return FileInfo(
            filename=filename,
            user="Unknown",
            report_name=name_without_ext
        )

    except Exception as e:
        logger.warning(f"Error parsing filename {filename}: {e}")
        return FileInfo(
            filename=filename,
            user="Unknown",
            report_name=filename.rsplit(".", 1)[0]
        )


def get_combined_report_info() -> Optional[CombinedReportInfo]:
    """Get information about the most recent combined report.

    Returns:
        CombinedReportInfo object or None if no combined report exists
    """
    try:
        reports_dir = get_reports_directory(REPORTS_DIR)
        combined_files = sorted(
            [f for f in os.listdir(reports_dir)
             if f.startswith(COMBINED_REPORT_PREFIX)],
            reverse=True
        )

        if not combined_files:
            return None

        latest_combined = combined_files[0]
        file_path = reports_dir / latest_combined

        if file_path.exists():
            file_stats = os.stat(file_path)
            return CombinedReportInfo(
                filename=latest_combined,
                size=file_stats.st_size,
                modified=datetime.fromtimestamp(file_stats.st_mtime)
            )

        return None

    except Exception as e:
        logger.debug(f"Error checking for combined report: {e}")
        return None


def monitor_scraper_logs() -> None:
    """Monitor scraper logs for supplementary information.

    Note: Critical errors are now handled directly through ScraperResult.
    This function primarily captures supplementary log information.
    """
    log_file_path = get_log_file_path("app.log")

    if not os.path.exists(log_file_path):
        return

    last_position = 0

    while app_state.get_download_status():
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                f.seek(last_position)
                f.readlines()  # Read new lines
                last_position = f.tell()
        except Exception as e:
            logger.debug(f"Error monitoring logs: {e}")

        time.sleep(2)


def run_scraper() -> None:
    """Execute the scraper in a background thread.

    This function manages the scraper execution, log monitoring,
    and notification handling.
    """
    try:
        app_state.set_download_status(True)
        app_state.clear_notifications()
        logger.info("Starting scraper process")

        # Start log monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_scraper_logs,
            daemon=True
        )
        monitor_thread.start()

        users = load_users()
        if not users:
            logger.warning("No users found, scraper may not function properly")
            app_state.add_notification(
                "No users configured for scraping",
                "warning"
            )

        # Import and run scraper
        try:
            from scraper import run_scraper_for_users, ScraperResult
            result: ScraperResult = run_scraper_for_users(
                USERS_FILE,
                verbose=False
            )

            # Process results and add notifications
            _process_scraper_result(result)

        except ImportError as e:
            logger.error(f"Failed to import scraper module: {e}")
            app_state.add_notification(
                f"Failed to import scraper module: {e}",
                "error"
            )
        except Exception as e:
            logger.error(f"Error in scraper execution: {e}")
            app_state.add_notification(
                f"Error in scraper execution: {e}",
                "error"
            )

    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        app_state.add_notification(f"Error running scraper: {e}", "error")
    finally:
        app_state.set_download_status(False)
        logger.info("Scraper process finished")


def _process_scraper_result(result) -> None:
    """Process scraper result and add appropriate notifications.

    Args:
        result: ScraperResult object from scraper execution
    """
    if result.success:
        logger.info("Scraper completed successfully")
        if result.users_processed < result.total_users:
            # Partial success
            app_state.add_notification(
                f"Scraper completed: {result.users_processed}/"
                f"{result.total_users} users successful",
                "warning"
            )
        else:
            # Complete success
            app_state.add_notification(
                f"All {result.users_processed} users processed successfully",
                "success"
            )
    else:
        logger.error("Scraper failed - no users processed successfully")
        error_summary = result.get_error_summary()
        app_state.add_notification(error_summary, "error")

    # Add individual user errors
    for user_result in result.user_results:
        if not user_result.success:
            if user_result.error_type == "product_access":
                app_state.add_notification(
                    f"User '{user_result.username}': {user_result.error}",
                    "error"
                )
            elif user_result.error_type == "login":
                app_state.add_notification(
                    f"User '{user_result.username}': "
                    f"Login failed - check credentials",
                    "error"
                )

    # Add warnings
    for warning in result.warnings:
        app_state.add_notification(warning, "warning")


def get_report_data() -> Dict[str, Any]:
    """Generate report presentation data.

    This aggregates data from various report files for the
    presentation view.

    Returns:
        Dictionary with all report presentation data
    """
    # Load configuration
    config = load_config()
    date_filter = config.date_filter
    custom_start = config.custom_start_date
    custom_end = config.custom_end_date

    # Generate date strings
    date_range = get_date_range_string(date_filter, custom_start, custom_end)
    subtitle = get_subtitle_string(date_filter, custom_start, custom_end)

    # Get summary data from reports
    summary = get_school_summary(REPORTS_DIR)
    teacher_summaries = get_teacher_summaries(REPORTS_DIR)
    teacher_usage_summaries = get_teacher_usage_summaries(REPORTS_DIR)
    skills_summary = get_skills_summary(REPORTS_DIR)
    overall_skills_table = get_overall_skills_table(REPORTS_DIR)
    level_up_progress = get_level_up_progress_data(REPORTS_DIR)
    top_readers = get_top_readers_per_classroom(REPORTS_DIR)
    classroom_comparison = get_teacher_comparison_data(REPORTS_DIR)
    assignment_reports = get_assignment_data(REPORTS_DIR)
    assessment_reports = get_assessment_data(REPORTS_DIR)

    return {
        # Slide 1: Title
        "report_title": "REPORTE DE USO",
        "institution": config.institution_name,
        "program_name": config.program_name,
        "date_range": date_range,
        "logos": [{"text": "b1 tech"}],

        # Slide 2: School Overview
        "school_overview": _build_school_overview(summary, subtitle),

        # Slide 3: Detailed Activities
        "detailed_activities": _build_detailed_activities(
            teacher_summaries,
            subtitle
        ),

        # Slide 5: Detailed Teachers
        "detailed_teachers": _build_detailed_teachers(
            teacher_usage_summaries,
            subtitle
        ),

        # Skills Summary (before per-classroom skills)
        "skills_summary": _build_skills_summary(skills_summary, overall_skills_table, subtitle),

        # Overall Skills Table (after summary, before per-classroom)
        "overall_skills_table": overall_skills_table if overall_skills_table else [],

        # Slide 5: Level Up Progress
        "level_up_progress": (
            level_up_progress if level_up_progress else []
        ),

        # Slide 6: Top Readers
        "top_readers": {
            "title": "Top Lectores",
            "subtitle": subtitle,
            "global_top": top_readers["global_top"] if top_readers else [],
            "by_teacher": top_readers["by_teacher"] if top_readers else []
        },

        # Slide 7: School Comparison
        "classroom_comparison": (
            classroom_comparison if classroom_comparison
            else {"labels": [], "listen": [], "read": [], "quiz": []}
        ),

        # Assignment Reports
        "assignment_reports": assignment_reports if assignment_reports else [],

        # Assessment Reports
        "assessment_reports": assessment_reports if assessment_reports else [],

        # Skills aggregate filter type (for dynamic column headers)
        "aggregate_skill_by_filter": config.aggregate_skill_by_filter
    }


def _build_school_overview(
    summary: Optional[Dict[str, Any]],
    subtitle: str
) -> Dict[str, Any]:
    """Build school overview data for presentation.

    Args:
        summary: School summary data
        subtitle: Date subtitle string

    Returns:
        Dictionary with formatted school overview data
    """
    total_activities = summary.get("total_activities", 0) if summary else 0

    # Calculate percentages
    if summary and total_activities > 0:
        listen_pct = round(
            summary["total_listen"] / total_activities * 100, 1
        )
        read_pct = round(
            summary["total_read"] / total_activities * 100, 1
        )
        quiz_pct = round(
            summary["total_quizzes"] / total_activities * 100, 1
        )
    else:
        listen_pct, read_pct, quiz_pct = 28.8, 34.6, 36.5

    active_teachers = summary.get('active_teachers', 0) if summary else 0
    inactive_teachers = summary.get('inactive_teachers', 0) if summary else 0
    total_teachers = active_teachers + inactive_teachers

    active_students = summary.get('active_students', 0) if summary else 0
    inactive_students = summary.get('inactive_students', 0) if summary else 0
    total_students = active_students + inactive_students

    return {
        "title": "RESUMEN DE USO",
        "subtitle": subtitle,
        "stats": [
            {
                "number": f"{active_teachers}/{total_teachers}",
                "label": "Docentes"
            },
            {
                "number": f"{active_students}/{total_students}",
                "label": "Estudiantes"
            }
        ],
        "activities": [
            {
                "number": str(summary.get("total_listen", 0) if summary else 0),
                "name": "Listen"
            },
            {
                "number": str(summary.get("total_read", 0) if summary else 0),
                "name": "Read"
            },
            {
                "number": str(summary.get("total_quizzes", 0) if summary else 0),
                "name": "Quiz"
            }
        ],
        "total_activities": f"{total_activities:,}",
        "activity_descriptions": [
            {
                "icon": "headphones",
                "text": "Listen: Número de audiciones completadas"
            },
            {
                "icon": "menu_book",
                "text": "Read: Número de lecturas completadas"
            },
            {
                "icon": "quiz",
                "text": "Quiz: Número de cuestionarios completados"
            }
        ],
        "chart_data": [listen_pct, read_pct, quiz_pct]
    }


def _build_detailed_activities(
    teacher_summaries: Optional[List[Dict[str, Any]]],
    subtitle: str
) -> Dict[str, Any]:
    """Build detailed activities data for presentation.

    Args:
        teacher_summaries: List of teacher summary dictionaries
        subtitle: Date subtitle string

    Returns:
        Dictionary with formatted detailed activities data
    """
    if not teacher_summaries:
        return {
            "title": "Detalle Total Actividades",
            "subtitle": subtitle,
            "activity_summary": [
                {"icon": "headphones", "number": "0", "name": "Listen"},
                {"icon": "menu_book", "number": "0", "name": "Read"},
                {"icon": "quiz", "number": "0", "name": "Quiz"}
            ],
            "teachers": [],
            "total": {
                "students": 0, "students_used": 0, "usage": 0,
                "listen": 0, "read": 0, "quiz": 0,
                "interactivity": 0, "practice_recording": 0
            }
        }

    total_listen = int(sum(s["listen"] for s in teacher_summaries))
    total_read = int(sum(s["read"] for s in teacher_summaries))
    total_quiz = int(sum(s["quiz"] for s in teacher_summaries))
    total_students = sum(s["students"] for s in teacher_summaries)

    # Calculate average usage
    if total_students > 0:
        avg_usage = round(
            sum(s["usage"] * s["students"] for s in teacher_summaries)
            / total_students,
            1
        )
    else:
        avg_usage = 0

    return {
        "title": "Detalle Total Actividades",
        "subtitle": subtitle,
        "activity_summary": [
            {"icon": "headphones", "number": str(total_listen), "name": "Listen"},
            {"icon": "menu_book", "number": str(total_read), "name": "Read"},
            {"icon": "quiz", "number": str(total_quiz), "name": "Quiz"}
        ],
        "teachers": [
            {
                "name": s["name"],
                "students": s["students"],
                "students_used": s.get("students_used", 0),
                "usage": s["usage"],
                "listen": int(s["listen"]),
                "read": int(s["read"]),
                "quiz": int(s["quiz"]),
                "interactivity": int(s["interactivity"]),
                "practice_recording": int(s["practice_recording"])
            }
            for s in teacher_summaries
        ],
        "total": {
            "students": total_students,
            "students_used": sum(
                s.get("students_used", 0) for s in teacher_summaries
            ),
            "usage": avg_usage,
            "listen": total_listen,
            "read": total_read,
            "quiz": total_quiz,
            "interactivity": int(
                sum(s["interactivity"] for s in teacher_summaries)
            ),
            "practice_recording": int(
                sum(s["practice_recording"] for s in teacher_summaries)
            )
        }
    }


def _build_detailed_teachers(
    teacher_usage_summaries: Optional[List[Dict[str, Any]]],
    subtitle: str
) -> Dict[str, Any]:
    """Build detailed teachers data for presentation.

    Creates the "Detalle Total Docentes" slide with raw teacher usage data.
    Shows actual counts without percentages or progress bars.

    Args:
        teacher_usage_summaries: List of teacher usage summary dictionaries
        subtitle: Date subtitle string

    Returns:
        Dictionary with formatted detailed teachers data
    """
    if not teacher_usage_summaries:
        return {
            "title": "DETALLE TOTAL DOCENTES",
            "subtitle": subtitle,
            "activity_summary": [
                {"icon": "menu_book", "number": "0", "name": "Texts"},
                {"icon": "school", "number": "0", "name": "Instruction"},
                {"icon": "edit", "number": "0", "name": "Practice"},
                {"icon": "quiz", "number": "0", "name": "Quizzes"}
            ],
            "teachers": [],
            "total": {
                "texts": 0,
                "instruction": 0,
                "practice": 0,
                "quizzes": 0,
                "total": 0
            }
        }

    # Calculate totals
    total_texts = sum(s["texts"] for s in teacher_usage_summaries)
    total_instruction = sum(s["instruction"] for s in teacher_usage_summaries)
    total_practice = sum(s["practice"] for s in teacher_usage_summaries)
    total_quizzes = sum(s["quizzes"] for s in teacher_usage_summaries)
    total_all = sum(s["total"] for s in teacher_usage_summaries)

    return {
        "title": "DETALLE TOTAL DOCENTES",
        "subtitle": subtitle,
        "activity_summary": [
            {"icon": "menu_book", "number": str(total_texts), "name": "Texts"},
            {"icon": "school", "number": str(total_instruction), "name": "Instruction"},
            {"icon": "edit", "number": str(total_practice), "name": "Practice"},
            {"icon": "quiz", "number": str(total_quizzes), "name": "Quizzes"}
        ],
        "teachers": [
            {
                "name": s["name"],
                "texts": s["texts"],
                "instruction": s["instruction"],
                "practice": s["practice"],
                "quizzes": s["quizzes"],
                "total": s["total"]
            }
            for s in teacher_usage_summaries
        ],
        "total": {
            "texts": total_texts,
            "instruction": total_instruction,
            "practice": total_practice,
            "quizzes": total_quizzes,
            "total": total_all
        }
    }


def _build_skills_summary(
    summary: Optional[Dict[str, Any]],
    overall_skills_table: Optional[List[Dict[str, Any]]],
    subtitle: str
) -> Dict[str, Any]:
    """Build skills summary data for presentation.

    Args:
        summary: Skills summary data from get_skills_summary()
        subtitle: Date subtitle string

    Returns:
        Dictionary with formatted skills summary data
    """
    if not summary:
        return {
            "title": "RESUMEN DE HABILIDADES",
            "subtitle": subtitle,
            "stats": [],
            "totals": {"correct": 0, "total": 0, "accuracy": 0},
            "top_skills": [],
            "chart_data": [0, 0, 0]
        }

    accuracy_dist = summary.get("accuracy_distribution", {})

    # Use top 5 skills from overall skills table if available, otherwise from summary
    if overall_skills_table:
        # Sort by accuracy descending and take top 5
        sorted_skills = sorted(overall_skills_table, key=lambda x: x["accuracy"], reverse=True)
        top_skills = sorted_skills[:5]
    else:
        top_skills = summary.get("top_skills", [])[:5]

    return {
        "title": "RESUMEN DE HABILIDADES",
        "subtitle": subtitle,
        "stats": [
            {
                "number": str(summary.get("total_classrooms", 0)),
                "label": "Institución educativa"
            },
            {
                "number": f"{summary.get('overall_accuracy', 0)}%",
                "label": "Precisión General"
            }
        ],
        "totals": {
            "correct": summary.get("total_correct", 0),
            "total": summary.get("total_questions", 0),
            "accuracy": summary.get("overall_accuracy", 0)
        },
        "top_skills": top_skills,
        "chart_data": [
            accuracy_dist.get("high", 0),
            accuracy_dist.get("medium", 0),
            accuracy_dist.get("low", 0)
        ]
    }


@app.route("/", methods=["GET"])
def index():
    """Main page displaying reports and configuration.

    Returns:
        Rendered template with report files and configuration
    """
    try:
        reports_dir = get_reports_directory(REPORTS_DIR)
        raw_files = get_report_files(str(reports_dir))

        # Filter out combined reports
        raw_files = [
            f for f in raw_files
            if not f.startswith(COMBINED_REPORT_PREFIX)
        ]

        # Parse file information
        files_with_info = [parse_file_info(f) for f in raw_files]

        # Group files by user
        files_by_user: Dict[str, List[FileInfo]] = {}
        for file_info in files_with_info:
            user = file_info.user
            if user not in files_by_user:
                files_by_user[user] = []
            files_by_user[user].append(file_info)

        # Get combined report info
        combined_report = get_combined_report_info()

        # Load configuration
        config = load_config()

        # Convert dates for HTML display
        custom_start_html = (
            format_date_for_html_input(config.custom_start_date)
            if config.custom_start_date else ""
        )
        custom_end_html = (
            format_date_for_html_input(config.custom_end_date)
            if config.custom_end_date else ""
        )

        users = load_users()

        return render_template(
            "scrapper.html",
            files=raw_files,
            files_with_info=files_with_info,
            files_by_user=files_by_user,
            combined_report=(
                {
                    "filename": combined_report.filename,
                    "size": combined_report.size,
                    "modified": combined_report.modified
                } if combined_report else None
            ),
            download_in_progress=app_state.get_download_status(),
            date_filters=DATE_FILTERS,
            selected_date_filter=config.date_filter,
            custom_start_date=custom_start_html,
            custom_end_date=custom_end_html,
            products_filters=PRODUCTS_FILTERS,
            selected_products_filter=config.products_filter,
            skill_filters=SKILL_FILTERS,
            selected_skill_filter=config.skill_filter,
            aggregate_skill_by_filters=AGGREGATE_SKILL_BY_FILTERS,
            selected_aggregate_skill_by_filter=config.aggregate_skill_by_filter,
            language_filters=LANGUAGE_FILTERS,
            selected_language_filter=config.language_filter,
            status_filters=STATUS_FILTERS,
            selected_status_filter=config.status_filter,
            tabs=TABS,
            selected_tabs=config.tabs.to_dict(),
            selected_institution_name=config.institution_name,
            selected_program_name=config.program_name,
            users=users
        )

    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/set-filter", methods=["POST"])
def set_filter():
    """Update filter configuration from form data.

    Returns:
        Redirect to index page or JSON error
    """
    try:
        config = load_config()

        # Update date filter
        date_filter = request.form.get("date_filter", DATE_FILTERS[0])
        if date_filter not in DATE_FILTERS:
            logger.warning(f"Invalid date filter received: {date_filter}")
            date_filter = DATE_FILTERS[0]
        config.date_filter = date_filter

        # Handle custom dates
        if date_filter == "Custom":
            custom_start = request.form.get("custom_start_date", "").strip()
            custom_end = request.form.get("custom_end_date", "").strip()

            if not custom_start or not custom_end:
                return jsonify({
                    "error": "Please provide both start and end dates"
                }), 400

            # Validate date range
            is_valid, error_msg = validate_date_range(
                custom_start,
                custom_end
            )

            if not is_valid:
                logger.warning(f"Invalid date range: {error_msg}")
                return jsonify({"error": error_msg}), 400

            # Convert and store dates
            config.custom_start_date = format_date_for_storage(custom_start)
            config.custom_end_date = format_date_for_storage(custom_end)

            logger.info(
                f"Custom date range set: {config.custom_start_date} "
                f"to {config.custom_end_date}"
            )
        else:
            config.custom_start_date = ""
            config.custom_end_date = ""

        # Update products filter
        products_filter = request.form.get(
            "products_filter",
            PRODUCTS_FILTERS[0]
        )
        if products_filter not in PRODUCTS_FILTERS:
            logger.warning(
                f"Invalid products filter received: {products_filter}"
            )
            products_filter = PRODUCTS_FILTERS[0]
        config.products_filter = products_filter

        # Update skill filter
        skill_filter = request.form.get(
            "skill_filter",
            SKILL_FILTERS[0]
        )
        if skill_filter not in SKILL_FILTERS:
            logger.warning(
                f"Invalid skill filter received: {skill_filter}"
            )
            skill_filter = SKILL_FILTERS[0]
        config.skill_filter = skill_filter

        # Update aggregate skill by filter
        aggregate_skill_by_filter = request.form.get(
            "aggregate_skill_by_filter",
            AGGREGATE_SKILL_BY_FILTERS[0]
        )
        if aggregate_skill_by_filter not in AGGREGATE_SKILL_BY_FILTERS:
            logger.warning(
                f"Invalid aggregate skill by filter received: {aggregate_skill_by_filter}"
            )
            aggregate_skill_by_filter = AGGREGATE_SKILL_BY_FILTERS[0]
        config.aggregate_skill_by_filter = aggregate_skill_by_filter

        # Update language filter
        language_filter = request.form.get(
            "language_filter",
            LANGUAGE_FILTERS[0]
        )
        if language_filter not in LANGUAGE_FILTERS:
            logger.warning(
                f"Invalid language filter received: {language_filter}"
            )
            language_filter = LANGUAGE_FILTERS[0]
        config.language_filter = language_filter

        # Update status filter
        status_filter = request.form.get(
            "status_filter",
            STATUS_FILTERS[0]
        )
        if status_filter not in STATUS_FILTERS:
            logger.warning(
                f"Invalid status filter received: {status_filter}"
            )
            status_filter = STATUS_FILTERS[0]
        config.status_filter = status_filter

        # Update tabs selection
        selected_tabs = request.form.getlist("tabs")
        tabs_dict = {
            tab["name"]: (tab["name"] in selected_tabs)
            for tab in TABS
        }
        from config import TabsConfig
        config.tabs = TabsConfig.from_dict(tabs_dict)

        # Update institution name
        institution_name = request.form.get(
            "institution_name",
            config.institution_name
        ).strip()
        if institution_name:
            config.institution_name = institution_name

        # Update program name
        program_name = request.form.get(
            "program_name",
            config.program_name
        ).strip()
        if program_name:
            config.program_name = program_name

        save_config(config)
        logger.info(
            f"Filter configuration updated: date={date_filter}, "
            f"products={products_filter}, skill={skill_filter}, "
            f"aggregate_by={aggregate_skill_by_filter}, "
            f"language={language_filter}, status={status_filter}, "
            f"tabs={selected_tabs}, institution={institution_name}"
        )

        return redirect(url_for("index"))

    except Exception as e:
        logger.error(f"Error updating filter configuration: {e}")
        return jsonify({"error": "Failed to update configuration"}), 500


@app.route("/download/<filename>")
def download(filename: str):
    """Download a specific report file.

    Args:
        filename: Name of the file to download

    Returns:
        File download or JSON error
    """
    try:
        # Security check
        if not validate_filename(filename):
            logger.warning(f"Potentially malicious filename: {filename}")
            return jsonify({"error": "Invalid filename"}), 400

        reports_dir = get_reports_directory(REPORTS_DIR)
        file_path = reports_dir / filename

        if not file_path.exists():
            logger.warning(f"Requested file not found: {filename}")
            return jsonify({"error": "File not found"}), 404

        logger.info(f"Downloading file: {filename}")
        return send_from_directory(
            str(reports_dir),
            filename,
            as_attachment=True
        )

    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({"error": "Download failed"}), 500


@app.route("/download-combined-reports")
def download_combined_reports():
    """Download the most recent combined all reports file.

    Returns:
        File download or JSON error
    """
    try:
        reports_dir = get_reports_directory(REPORTS_DIR)
        combined_files = sorted(
            [f for f in os.listdir(reports_dir)
             if f.startswith(COMBINED_REPORT_PREFIX)],
            reverse=True
        )

        if not combined_files:
            logger.info("No combined all reports file available")
            return jsonify({
                "error": "No combined all reports file available"
            }), 404

        latest_combined = combined_files[0]

        # Security check
        if not validate_filename(latest_combined):
            logger.warning(f"Potentially malicious filename: {latest_combined}")
            return jsonify({"error": "Invalid filename"}), 400

        file_path = reports_dir / latest_combined
        if not file_path.exists():
            logger.warning(f"Combined file not found: {latest_combined}")
            return jsonify({"error": "File not found"}), 404

        logger.info(f"Downloading combined reports: {latest_combined}")
        return send_from_directory(
            str(reports_dir),
            latest_combined,
            as_attachment=True
        )

    except Exception as e:
        logger.error(f"Error downloading combined reports: {e}")
        return jsonify({"error": "Download failed"}), 500


@app.route("/get-combined-reports-status")
def get_combined_reports_status():
    """Check if a combined all reports file exists.

    Returns:
        JSON with existence status and file information
    """
    try:
        combined_report = get_combined_report_info()

        if combined_report:
            return jsonify({
                "exists": True,
                "filename": combined_report.filename,
                "size": combined_report.size,
                "modified": combined_report.modified.isoformat()
            })
        else:
            return jsonify({"exists": False})

    except Exception as e:
        logger.error(f"Error checking combined reports status: {e}")
        return jsonify({"exists": False, "error": str(e)})


@app.route("/scrape", methods=["POST"])
def scrape():
    """Start the scraping process.

    Returns:
        JSON with status
    """
    try:
        if not app_state.get_download_status():
            logger.info("Starting new scrape job")
            threading.Thread(target=run_scraper, daemon=True).start()
            return jsonify({"status": "started"})
        else:
            logger.info("Scrape request received but job already running")
            return jsonify({"status": "already_running"})

    except Exception as e:
        logger.error(f"Error starting scrape job: {e}")
        return jsonify({"error": "Failed to start scraper"}), 500


@app.route("/scrape-status")
def scrape_status():
    """Get current scraping status.

    Returns:
        JSON with scraping status
    """
    try:
        return jsonify({"in_progress": app_state.get_download_status()})
    except Exception as e:
        logger.error(f"Error getting scrape status: {e}")
        return jsonify({"error": "Failed to get status"}), 500


@app.route("/scrape-notifications")
def scrape_notifications():
    """Get current scraper notifications.

    Returns:
        JSON with notifications list and status
    """
    try:
        return jsonify({
            "notifications": app_state.get_notifications(),
            "in_progress": app_state.get_download_status()
        })
    except Exception as e:
        logger.error(f"Error getting scrape notifications: {e}")
        return jsonify({"notifications": [], "in_progress": False})


@app.route("/clear-notifications", methods=["POST"])
def clear_notifications():
    """Clear all notifications.

    Returns:
        JSON with status
    """
    try:
        app_state.clear_notifications()
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        return jsonify({"error": "Failed to clear notifications"}), 500


@app.route("/delete-all-reports", methods=["POST"])
def delete_all_reports():
    """Delete all report files from the reports directory.

    Returns:
        JSON with deletion status and count
    """
    try:
        reports_dir = get_reports_directory(REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)

        files_deleted = 0
        for file_path in reports_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                files_deleted += 1
                logger.info(f"Deleted report file: {file_path.name}")

        logger.info(f"Successfully deleted {files_deleted} report files")
        return jsonify({"status": "ok", "files_deleted": files_deleted})

    except Exception as e:
        logger.error(f"Error deleting all reports: {e}")
        return jsonify({
            "error": f"Failed to delete reports: {str(e)}"
        }), 500


@app.route("/scrape-logs")
def scrape_logs():
    """Get recent scraper logs (legacy endpoint for compatibility).

    Returns:
        JSON with warnings and errors lists
    """
    try:
        notifications = app_state.get_notifications()

        warnings = [
            n["message"] for n in notifications
            if n["type"] == "warning"
        ]
        errors = [
            n["message"] for n in notifications
            if n["type"] == "error"
        ]

        return jsonify({"warnings": warnings, "errors": errors})

    except Exception as e:
        logger.error(f"Error getting scrape logs: {e}")
        return jsonify({"warnings": [], "errors": []})


@app.route("/get-users", methods=["GET"])
def get_users():
    """Get list of configured users.

    Returns:
        JSON with users list
    """
    try:
        users = load_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": "Failed to load users"}), 500


@app.route("/save-users", methods=["POST"])
def save_users_route():
    """Save users configuration via JSON API.

    Returns:
        JSON with status
    """
    try:
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400

        users = request.json.get("users", [])

        # Validate users data
        if not isinstance(users, list):
            return jsonify({"error": "Users must be a list"}), 400

        for user in users:
            if not validate_user_data(user):
                return jsonify({
                    "error": "Each user must have username and password"
                }), 400

        save_users(users)
        logger.info(f"Saved {len(users)} users via API")
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"Error saving users: {e}")
        return jsonify({"error": "Failed to save users"}), 500


@app.route("/clear-all", methods=["POST"])
def clear_all():
    """Clear all users and reports.

    Returns:
        JSON with status, files deleted count, and users cleared confirmation
    """
    try:
        # Clear all reports
        reports_dir = get_reports_directory(REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)

        files_deleted = 0
        for file_path in reports_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                files_deleted += 1
                logger.info(f"Deleted report file: {file_path.name}")

        # Clear all users
        save_users([])
        logger.info("Successfully cleared all users")

        logger.info(f"Successfully cleared {files_deleted} reports and all users")
        return jsonify({
            "status": "ok",
            "files_deleted": files_deleted,
            "users_cleared": True
        })

    except Exception as e:
        logger.error(f"Error clearing all data: {e}")
        return jsonify({
            "error": f"Failed to clear data: {str(e)}"
        }), 500


@app.route("/upload-users", methods=["POST"])
def upload_users():
    """Upload users configuration from JSON file.

    Returns:
        JSON with status and message
    """
    try:
        if "users_file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["users_file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.endswith(".json"):
            return jsonify({"error": "File must be a JSON file"}), 400

        # Read and parse JSON
        file_content = file.read().decode("utf-8")
        import json
        try:
            users_data = json.loads(file_content)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON file format"}), 400

        # Validate structure
        if not isinstance(users_data, list):
            return jsonify({
                "error": "JSON file must contain an array of users"
            }), 400

        for user in users_data:
            if not validate_user_data(user):
                return jsonify({
                    "error": "Each user must have username and password"
                }), 400

        save_users(users_data)
        logger.info(f"Successfully uploaded {len(users_data)} users from file")

        return jsonify({
            "status": "ok",
            "message": f"Successfully uploaded {len(users_data)} users"
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in uploaded file: {e}")
        return jsonify({"error": "Invalid JSON file format"}), 400
    except UnicodeDecodeError as e:
        logger.error(f"File encoding error: {e}")
        return jsonify({
            "error": "File encoding not supported, please use UTF-8"
        }), 400
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500


@app.route("/report")
def report():
    """Display the professional report presentation.

    Returns:
        Rendered report template
    """
    try:
        data = get_report_data()
        return render_template("report.html", **data)
    except Exception as e:
        logger.error(f"Error rendering report: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/logs/app")
def get_app_logs():
    """Get the contents of app.log file.

    Returns:
        Plain text log contents or JSON error
    """
    try:
        log_file_path = get_log_file_path("app.log")

        if not os.path.exists(log_file_path):
            logger.warning(f"app.log file not found at {log_file_path}")
            return jsonify({"error": "Log file not found"}), 404

        with open(log_file_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        return log_content, 200, {"Content-Type": "text/plain; charset=utf-8"}

    except Exception as e:
        logger.error(f"Error reading app.log: {e}")
        return jsonify({"error": "Failed to read log file"}), 500


@app.route("/templates/images/<filename>")
def serve_template_image(filename: str):
    """Serve images from templates/images directory.

    Args:
        filename: Image filename

    Returns:
        Image file or JSON error
    """
    try:
        return send_from_directory("templates/images", filename)
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        return jsonify({"error": "Image not found"}), 404


def cleanup_on_startup() -> None:
    """Clean up reports and users on application startup.

    This function performs the following cleanup operations:
    1. Removes all files from reports directories
    2. Clears all configured users

    All errors are logged but do not prevent application startup.
    """
    from path_helpers import get_all_reports_directories

    # Clean up reports directories
    try:
        directories_to_clean = get_all_reports_directories(REPORTS_DIR)
        total_files_removed = 0

        for reports_dir in directories_to_clean:
            try:
                reports_dir.mkdir(parents=True, exist_ok=True)

                files_removed = 0
                for file_path in reports_dir.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                        files_removed += 1

                if files_removed > 0:
                    logger.info(
                        f"Cleaned up {files_removed} files from {reports_dir}"
                    )
                    total_files_removed += files_removed
                else:
                    logger.info(f"Reports directory {reports_dir} is clean")

            except Exception as e:
                logger.warning(
                    f"Error cleaning up reports directory {reports_dir}: {e}"
                )

        if total_files_removed > 0:
            logger.info(
                f"Total cleaned up {total_files_removed} files from "
                f"all reports directories"
            )
        else:
            logger.info("All reports directories are clean")

    except Exception as e:
        logger.error(f"Error cleaning up reports directories: {e}")

    # Clean up users
    try:
        logger.info("Clearing all configured users on startup")
        save_users([])
        logger.info("Successfully cleared all users")
    except FileOperationError as e:
        logger.error(f"Failed to clear users during startup: {e}")
    except Exception as e:
        logger.error(f"Unexpected error clearing users during startup: {e}")


def open_browser(
    host: str = "localhost",
    port: int = 5000,
    delay: float = 1.5
) -> None:
    """Open the default web browser to the application URL.

    Args:
        host: Host address (use localhost for browser access)
        port: Port number
        delay: Delay in seconds before opening browser
    """
    def _open_browser():
        time.sleep(delay)
        url = f"http://{host}:{port}"
        try:
            logger.info(f"Opening browser to {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")
            logger.info(f"Please open your browser manually and go to {url}")

    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()


if __name__ == "__main__":
    # Configuration
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    BROWSER_HOST = "localhost"
    AUTO_OPEN_BROWSER = (
        os.getenv("AUTO_OPEN_BROWSER", "true").lower() == "true"
    )

    cleanup_on_startup()
    clear_log_file("app.log")
    logger.info("Cleared app.log file")
    logger.info("Starting Flask application")
    logger.info(f"Server will be available at http://{BROWSER_HOST}:{PORT}")

    if AUTO_OPEN_BROWSER:
        open_browser(host=BROWSER_HOST, port=PORT)
        logger.info("Browser will open automatically in 1.5 seconds...")
    else:
        logger.info("Auto-open browser disabled. Open manually.")

    try:
        serve(app, host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
