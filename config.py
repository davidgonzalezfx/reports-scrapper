"""Configuration management for the reports scraper application.

This module provides classes and functions for managing application configuration
with proper validation and type safety.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from pathlib import Path

from constants import (
    CONFIG_FILE,
    DATE_FILTERS,
    PRODUCTS_FILTERS,
    SKILL_FILTERS,
    AGGREGATE_SKILL_BY_FILTERS,
    LANGUAGE_FILTERS,
    STATUS_FILTERS,
    TABS,
    DEFAULT_INSTITUTION_NAME,
    DATE_RANGE_MAX_CUSTOM
)

logger = logging.getLogger(__name__)


@dataclass
class TabsConfig:
    """Configuration for which report tabs are enabled."""

    usage_dashboard: bool = True
    teacher_usage: bool = True
    student_usage: bool = True
    student_skills: bool = True
    assignment_report: bool = True
    assessment_report: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> "TabsConfig":
        """Create TabsConfig from dictionary.

        Args:
            data: Dictionary mapping tab names to enabled status

        Returns:
            TabsConfig instance
        """
        return cls(
            usage_dashboard=data.get("Usage Dashboard", True),
            teacher_usage=data.get("Teacher Usage", True),
            student_usage=data.get("Student Usage", True),
            student_skills=data.get("Student Skills", True),
            assignment_report=data.get("Assignment Report", True),
            assessment_report=data.get("Assessment Report", True)
        )

    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary format expected by the application.

        Returns:
            Dictionary mapping tab names to enabled status
        """
        return {
            "Usage Dashboard": self.usage_dashboard,
            "Teacher Usage": self.teacher_usage,
            "Student Usage": self.student_usage,
            "Student Skills": self.student_skills,
            "Assignment Report": self.assignment_report,
            "Assessment Report": self.assessment_report
        }


@dataclass
class ScraperConfig:
    """Main configuration for the scraper application."""

    date_filter: str = "Today"
    custom_start_date: str = ""
    custom_end_date: str = ""
    products_filter: str = "All"
    skill_filter: str = "All"
    aggregate_skill_by_filter: str = "skill"
    language_filter: str = "All"
    status_filter: str = "All"
    tabs: TabsConfig = field(default_factory=TabsConfig)
    institution_name: str = DEFAULT_INSTITUTION_NAME

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration values are invalid
        """
        # Validate date filter
        if self.date_filter not in DATE_FILTERS:
            logger.warning(
                f"Invalid date filter '{self.date_filter}', "
                f"using default 'Today'"
            )
            self.date_filter = "Today"

        # Validate products filter
        if self.products_filter not in PRODUCTS_FILTERS:
            logger.warning(
                f"Invalid products filter '{self.products_filter}', "
                f"using default 'All'"
            )
            self.products_filter = "All"

        # Validate skill filter
        if self.skill_filter not in SKILL_FILTERS:
            logger.warning(
                f"Invalid skill filter '{self.skill_filter}', "
                f"using default 'All'"
            )
            self.skill_filter = "All"

        # Validate aggregate skill by filter
        if self.aggregate_skill_by_filter not in AGGREGATE_SKILL_BY_FILTERS:
            logger.warning(
                f"Invalid aggregate skill by filter '{self.aggregate_skill_by_filter}', "
                f"using default 'skill'"
            )
            self.aggregate_skill_by_filter = "skill"

        # Validate language filter
        if self.language_filter not in LANGUAGE_FILTERS:
            logger.warning(
                f"Invalid language filter '{self.language_filter}', "
                f"using default 'All'"
            )
            self.language_filter = "All"

        # Validate status filter
        if self.status_filter not in STATUS_FILTERS:
            logger.warning(
                f"Invalid status filter '{self.status_filter}', "
                f"using default 'All'"
            )
            self.status_filter = "All"

        # Validate custom dates if Custom filter is selected
        if self.date_filter == "Custom":
            if not self.custom_start_date or not self.custom_end_date:
                logger.warning(
                    "Custom date filter selected but dates not provided"
                )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScraperConfig":
        """Create ScraperConfig from dictionary.

        Args:
            data: Dictionary with configuration data

        Returns:
            ScraperConfig instance
        """
        tabs_data = data.get("tabs", {})
        tabs_config = TabsConfig.from_dict(tabs_data) if isinstance(
            tabs_data, dict
        ) else TabsConfig()

        return cls(
            date_filter=data.get("date_filter", "Today"),
            custom_start_date=data.get("custom_start_date", ""),
            custom_end_date=data.get("custom_end_date", ""),
            products_filter=data.get("products_filter", "All"),
            skill_filter=data.get("skill_filter", "All"),
            aggregate_skill_by_filter=data.get("aggregate_skill_by_filter", "skill"),
            tabs=tabs_config,
            institution_name=data.get(
                "institution_name", DEFAULT_INSTITUTION_NAME
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with configuration data
        """
        return {
            "date_filter": self.date_filter,
            "custom_start_date": self.custom_start_date,
            "custom_end_date": self.custom_end_date,
            "products_filter": self.products_filter,
            "skill_filter": self.skill_filter,
            "aggregate_skill_by_filter": self.aggregate_skill_by_filter,
            "tabs": self.tabs.to_dict(),
            "institution_name": self.institution_name
        }


def get_default_config() -> ScraperConfig:
    """Get default configuration.

    Returns:
        ScraperConfig with default values
    """
    tabs_dict = {tab["name"]: tab["default"] for tab in TABS}
    return ScraperConfig(
        date_filter=DATE_FILTERS[0],
        custom_start_date="",
        custom_end_date="",
        products_filter=PRODUCTS_FILTERS[0],
        skill_filter=SKILL_FILTERS[0],
        aggregate_skill_by_filter=AGGREGATE_SKILL_BY_FILTERS[0],
        tabs=TabsConfig.from_dict(tabs_dict),
        institution_name=DEFAULT_INSTITUTION_NAME
    )


def load_config(config_file: str = CONFIG_FILE) -> ScraperConfig:
    """Load configuration from file.

    Args:
        config_file: Path to configuration file

    Returns:
        ScraperConfig instance with loaded or default configuration
    """
    from utils import load_json

    config_data = load_json(config_file, None)

    if config_data is None:
        logger.info("No config file found, using defaults")
        return get_default_config()

    try:
        config = ScraperConfig.from_dict(config_data)
        logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}, using defaults")
        return get_default_config()


def save_config(
    config: ScraperConfig,
    config_file: str = CONFIG_FILE
) -> bool:
    """Save configuration to file.

    Args:
        config: ScraperConfig instance to save
        config_file: Path to configuration file

    Returns:
        True if save successful, False otherwise

    Raises:
        OSError: If save fails
    """
    from utils import save_json

    if not save_json(config.to_dict(), config_file):
        raise OSError("Failed to save configuration")

    logger.info("Configuration saved successfully")
    return True


def validate_custom_date_range(
    start_date: str,
    end_date: str,
    max_days: int = DATE_RANGE_MAX_CUSTOM
) -> tuple[bool, Optional[str]]:
    """Validate custom date range.

    Args:
        start_date: Start date in DD/MM/YYYY or YYYY-MM-DD format
        end_date: End date in DD/MM/YYYY or YYYY-MM-DD format
        max_days: Maximum allowed days in range

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid
    """
    from datetime import datetime

    if not start_date or not end_date:
        return False, "Both start and end dates are required"

    try:
        # Try DD/MM/YYYY format first
        try:
            start = datetime.strptime(start_date, "%d/%m/%Y")
            end = datetime.strptime(end_date, "%d/%m/%Y")
        except ValueError:
            # Try YYYY-MM-DD format
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

        # Validate range
        date_diff = (end - start).days

        if date_diff < 0:
            return False, "End date must be after start date"

        if date_diff > max_days:
            return False, f"Date range cannot exceed {max_days} days"

        return True, None

    except ValueError as e:
        return False, f"Invalid date format: {str(e)}"
