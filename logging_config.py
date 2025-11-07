"""Centralized logging configuration for the reports scraper application.

This module provides unified logging setup to eliminate duplicated logging
configuration across multiple modules.
"""

import logging
import sys
from typing import Optional
from pathlib import Path

from constants import LOG_FORMAT, LOG_FILE, SCRAPER_LOG_FILE
from path_helpers import get_log_file_path


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        log_file: Log file name (None for no file logging)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output to console
        file_output: Whether to output to file

    Returns:
        Configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if requested
    if file_output and log_file:
        log_path = get_log_file_path(log_file)
        try:
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except OSError as e:
            # Fallback to console only if file handler fails
            root_logger.error(f"Could not create log file '{log_path}': {e}")

    return root_logger


def setup_app_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging for the main Flask application.

    Args:
        verbose: Enable verbose (DEBUG) logging

    Returns:
        Configured logger for the app
    """
    level = logging.DEBUG if verbose else logging.INFO
    return setup_logging(
        log_file=LOG_FILE,
        level=level,
        console_output=True,
        file_output=True
    )


def setup_scraper_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging for the scraper module.

    Args:
        verbose: Enable verbose (DEBUG) logging

    Returns:
        Configured logger for the scraper
    """
    level = logging.DEBUG if verbose else logging.INFO
    return setup_logging(
        log_file=SCRAPER_LOG_FILE,
        level=level,
        console_output=True,
        file_output=True
    )


def clear_log_file(log_file: str) -> bool:
    """Clear the contents of a log file.

    Args:
        log_file: Name of the log file to clear

    Returns:
        True if successful, False otherwise
    """
    log_path = get_log_file_path(log_file)

    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('')
        logging.info(f"Cleared log file: {log_path}")
        return True
    except OSError as e:
        logging.error(f"Failed to clear log file '{log_path}': {e}")
        return False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)
