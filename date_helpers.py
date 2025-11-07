"""Date and time utilities for the reports scraper application.

This module provides functions for date formatting, parsing, range calculation,
and Spanish localization to eliminate code duplication.
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

from constants import (
    SPANISH_MONTHS,
    DATE_RANGE_LAST_7_DAYS,
    DATE_RANGE_LAST_30_DAYS,
    DATE_RANGE_LAST_90_DAYS,
    DATE_RANGE_LAST_YEAR,
    DATE_RANGE_MAX_CUSTOM
)

logger = logging.getLogger(__name__)


def get_spanish_month(month: int) -> str:
    """Convert month number to Spanish month name.

    Args:
        month: Month number (1-12)

    Returns:
        Spanish month name (e.g., "Enero", "Febrero")
        Returns "Enero" for invalid month numbers
    """
    return SPANISH_MONTHS.get(month, "Enero")


def format_date_spanish(date: datetime) -> str:
    """Format date in Spanish format.

    Args:
        date: Datetime object to format

    Returns:
        Formatted date string like "15 Marzo 2024"
    """
    return f"{date.day:02d} {get_spanish_month(date.month)} {date.year}"


def calculate_date_range(
    date_filter: str,
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None
) -> Tuple[datetime, datetime]:
    """Calculate start and end dates based on filter selection.

    Args:
        date_filter: Date filter name (Today, Last 7 Days, etc.)
        custom_start: Custom start date in DD/MM/YYYY format
        custom_end: Custom end date in DD/MM/YYYY format

    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    today = datetime.now()

    if date_filter == "Today":
        return today, today

    elif date_filter == "Last 7 Days":
        return today - timedelta(days=DATE_RANGE_LAST_7_DAYS), today

    elif date_filter == "Last 30 Days":
        return today - timedelta(days=DATE_RANGE_LAST_30_DAYS), today

    elif date_filter == "Last 90 Days":
        return today - timedelta(days=DATE_RANGE_LAST_90_DAYS), today

    elif date_filter == "Last Year":
        return today - timedelta(days=DATE_RANGE_LAST_YEAR), today

    elif date_filter == "Custom" and custom_start and custom_end:
        try:
            start_date = datetime.strptime(custom_start, "%d/%m/%Y")
            end_date = datetime.strptime(custom_end, "%d/%m/%Y")
            return start_date, end_date
        except ValueError as e:
            logger.warning(
                f"Failed to parse custom dates: {custom_start} - {custom_end}: {e}"
            )
            return today, today

    # Default fallback
    return today, today


def get_date_range_string(
    date_filter: str,
    custom_start_date: Optional[str] = None,
    custom_end_date: Optional[str] = None
) -> str:
    """Generate date range string based on selected filter.

    Args:
        date_filter: Date filter name
        custom_start_date: Custom start date in DD/MM/YYYY format
        custom_end_date: Custom end date in DD/MM/YYYY format

    Returns:
        Formatted date range string in Spanish
        For single day: "15 Marzo 2024"
        For range: "15 Marzo 2024 - 30 Abril 2024"
    """
    start_date, end_date = calculate_date_range(
        date_filter,
        custom_start_date,
        custom_end_date
    )

    # Single day format
    if start_date.date() == end_date.date():
        return format_date_spanish(start_date)

    # Range format
    start_str = format_date_spanish(start_date)
    end_str = format_date_spanish(end_date)
    return f"{start_str} - {end_str}"


def get_subtitle_string(
    date_filter: str,
    custom_start_date: Optional[str] = None,
    custom_end_date: Optional[str] = None
) -> str:
    """Generate subtitle string based on selected filter.

    This creates a compact date representation for report subtitles.

    Args:
        date_filter: Date filter name
        custom_start_date: Custom start date in DD/MM/YYYY format
        custom_end_date: Custom end date in DD/MM/YYYY format

    Returns:
        Formatted subtitle string in Spanish
        Examples:
        - Same month/year: "Marzo 2024"
        - Same year: "Marzo - Abril 2024"
        - Different years: "Marzo 2024 - Abril 2025"
    """
    start_date, end_date = calculate_date_range(
        date_filter,
        custom_start_date,
        custom_end_date
    )

    # Same year
    if start_date.year == end_date.year:
        # Same month
        if start_date.month == end_date.month:
            return f"{get_spanish_month(start_date.month)} {start_date.year}"
        # Different months, same year
        else:
            return (
                f"{get_spanish_month(start_date.month)} - "
                f"{get_spanish_month(end_date.month)} {end_date.year}"
            )
    # Different years
    else:
        return (
            f"{get_spanish_month(start_date.month)} {start_date.year} - "
            f"{get_spanish_month(end_date.month)} {end_date.year}"
        )


def parse_date_from_html_input(date_str: str) -> Optional[datetime]:
    """Parse date from HTML input type="date" format (YYYY-MM-DD).

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Failed to parse HTML date '{date_str}': {e}")
        return None


def format_date_for_html_input(date_str: str) -> Optional[str]:
    """Convert DD/MM/YYYY date to YYYY-MM-DD for HTML input.

    Args:
        date_str: Date string in DD/MM/YYYY format

    Returns:
        Date string in YYYY-MM-DD format or None if parsing fails
    """
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Failed to convert date '{date_str}' for HTML: {e}")
        return None


def format_date_for_storage(date_str: str) -> Optional[str]:
    """Convert YYYY-MM-DD date to DD/MM/YYYY for storage.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Date string in DD/MM/YYYY format or None if parsing fails
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d/%m/%Y")
    except ValueError as e:
        logger.error(f"Failed to convert date '{date_str}' for storage: {e}")
        return None


def convert_date_for_website(date_str: str) -> Optional[str]:
    """Convert DD/MM/YYYY date to MM/DD/YYYY for website input.

    The target website expects MM/DD/YYYY format for date inputs.

    Args:
        date_str: Date string in DD/MM/YYYY format

    Returns:
        Date string in MM/DD/YYYY format or None if parsing fails
    """
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.strftime("%m/%d/%Y")
    except ValueError as e:
        logger.error(f"Failed to convert date '{date_str}' for website: {e}")
        return None


def validate_date_range(
    start_date_str: str,
    end_date_str: str,
    date_format: str = "%Y-%m-%d",
    max_days: int = DATE_RANGE_MAX_CUSTOM
) -> Tuple[bool, Optional[str]]:
    """Validate that a date range is valid.

    Args:
        start_date_str: Start date string
        end_date_str: End date string
        date_format: Format of the date strings
        max_days: Maximum allowed days in range

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid
    """
    if not start_date_str or not end_date_str:
        return False, "Both start and end dates are required"

    try:
        start_date = datetime.strptime(start_date_str, date_format)
        end_date = datetime.strptime(end_date_str, date_format)

        date_diff = (end_date - start_date).days

        if date_diff < 0:
            return False, "End date must be after start date"

        if date_diff > max_days:
            return False, f"Date range cannot exceed {max_days} days"

        return True, None

    except ValueError as e:
        return False, f"Invalid date format: {str(e)}"


def get_current_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """Get current timestamp as a formatted string.

    Args:
        format_str: strftime format string

    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_str)
