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
    TABS,
    DEFAULT_INSTITUTION_NAME,
    DATE_RANGE_MAX_CUSTOM
)

logger = logging.getLogger(__name__)


@dataclass
class TabsConfig:
    """Configuration for which report tabs are enabled."""

    student_usage: bool = True
    skill: bool = True
    assignment: bool = True
    assessment: bool = True
    level_up_progress: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> "TabsConfig":
        """Create TabsConfig from dictionary.

        Args:
            data: Dictionary mapping tab names to enabled status

        Returns:
            TabsConfig instance
        """
        return cls(
            student_usage=data.get("Student Usage", True),
            skill=data.get("Skill", True),
            assignment=data.get("Assignment", True),
            assessment=data.get("Assessment", True),
            level_up_progress=data.get("Level Up Progress", True)
        )

    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary format expected by the application.

        Returns:
            Dictionary mapping tab names to enabled status
        """
        return {
            "Student Usage": self.student_usage,
            "Skill": self.skill,
            "Assignment": self.assessment,
            "Assessment": self.assessment,
            "Level Up Progress": self.level_up_progress
        }


@dataclass
class ScraperConfig:
    """Main configuration for the scraper application."""

    date_filter: str = "Today"
    custom_start_date: str = ""
    custom_end_date: str = ""
    products_filter: str = "All"
    skill_filter: str = "All"
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
