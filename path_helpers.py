"""Path resolution utilities for the reports scraper application.

This module provides centralized path handling for PyInstaller bundled applications
and development environments, eliminating code duplication.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Union, Optional, List

logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """Check if the application is running as a PyInstaller frozen executable.

    Returns:
        True if running as frozen executable, False otherwise
    """
    return getattr(sys, 'frozen', False)


def get_base_path() -> Path:
    """Get the base path for the application.

    For frozen executables, this returns sys._MEIPASS (PyInstaller temp directory).
    For development, this returns the current working directory.

    Returns:
        Path object representing the base application path
    """
    if is_frozen():
        # Running as PyInstaller executable
        base_path = Path(sys._MEIPASS)
        logger.debug(f"Running as frozen app, base path: {base_path}")
        return base_path
    else:
        # Running in development
        base_path = Path(os.path.abspath('.'))
        logger.debug(f"Running in development, base path: {base_path}")
        return base_path


def get_executable_dir() -> Path:
    """Get the directory containing the executable.

    For frozen executables, returns the directory containing the .exe/.app.
    For development, returns the current working directory.

    Returns:
        Path object representing the executable directory
    """
    if is_frozen():
        exe_dir = Path(os.path.dirname(sys.executable))
        logger.debug(f"Executable directory: {exe_dir}")
        return exe_dir
    else:
        return get_base_path()


def resolve_path(relative_path: Union[str, Path]) -> Path:
    """Resolve a relative path to an absolute path.

    Handles both development and PyInstaller frozen environments.

    Args:
        relative_path: Relative path to resolve (string or Path object)

    Returns:
        Absolute Path object
    """
    if isinstance(relative_path, str):
        relative_path = Path(relative_path)

    # If already absolute, return as-is
    if relative_path.is_absolute():
        return relative_path

    # Resolve against base path
    resolved = get_base_path() / relative_path
    logger.debug(f"Resolved '{relative_path}' to '{resolved}'")
    return resolved


def get_reports_directory(reports_dir: str = "reports") -> Path:
    """Get the reports directory path.

    For frozen apps, checks both internal (_MEIPASS) and external (next to exe).
    For development, uses the local reports directory.

    Args:
        reports_dir: Name of the reports directory

    Returns:
        Path to the reports directory (creates if doesn't exist)
    """
    if is_frozen():
        # Prefer external directory (next to exe) for user accessibility
        external_dir = get_executable_dir() / reports_dir
        external_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using external reports directory: {external_dir}")
        return external_dir
    else:
        # Development mode
        local_dir = Path(reports_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using local reports directory: {local_dir}")
        return local_dir


def get_all_reports_directories(reports_dir: str = "reports") -> List[Path]:
    """Get all possible reports directory paths.

    For frozen apps, returns both internal and external directories.
    For development, returns only the local directory.

    Args:
        reports_dir: Name of the reports directory

    Returns:
        List of Path objects for reports directories
    """
    directories = []

    if is_frozen():
        # External directory (next to executable)
        external_dir = get_executable_dir() / reports_dir
        if external_dir.exists():
            directories.append(external_dir)
            logger.debug(f"Found external reports dir: {external_dir}")

        # Internal directory (_MEIPASS)
        internal_dir = get_base_path() / reports_dir
        if internal_dir.exists():
            directories.append(internal_dir)
            logger.debug(f"Found internal reports dir: {internal_dir}")
    else:
        # Development mode - single directory
        local_dir = Path(reports_dir)
        if local_dir.exists():
            directories.append(local_dir)
            logger.debug(f"Found local reports dir: {local_dir}")

    return directories


def get_playwright_browsers_path() -> Path:
    """Get the path to Playwright browsers directory.

    Checks multiple locations and returns the first existing path.
    Priority: current working directory, then base path, then executable dir.

    Returns:
        Path to playwright-browsers directory
    """
    # Primary path: current working directory
    browsers_path = Path.cwd() / 'playwright-browsers'

    if not is_frozen():
        # Development mode
        logger.info(f"Using Playwright browsers path: {browsers_path}")
        if not browsers_path.exists():
            logger.warning(
                f"Playwright browsers directory does not exist: {browsers_path}. "
                f"You may need to run: python -m playwright install chromium"
            )
        return browsers_path

    # PyInstaller mode - check if primary path exists
    if browsers_path.exists():
        logger.info(f"Found Playwright browsers at: {browsers_path}")
        return browsers_path

    # Check alternative locations
    alternative_paths = [
        get_base_path() / 'playwright-browsers',
        get_executable_dir() / 'playwright-browsers',
    ]

    for alt_path in alternative_paths:
        if alt_path.exists():
            logger.info(f"Found Playwright browsers at alternative location: {alt_path}")
            return alt_path

    # No existing path found - return primary path and warn
    logger.warning(
        f"Playwright browsers not found at: {browsers_path}. "
        f"Browser may fail to launch."
    )
    return browsers_path


def setup_playwright_environment() -> bool:
    """Set up environment variables for Playwright.

    Sets PLAYWRIGHT_BROWSERS_PATH to the current directory's playwright-browsers folder.
    This must be called before importing playwright modules.

    Returns:
        Always returns True (path is always set, even if directory doesn't exist)
    """
    browsers_path = get_playwright_browsers_path()

    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers_path)
    logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to: {browsers_path}")

    # Also set MS_PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD to avoid downloading to cache
    if 'MS_PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD' not in os.environ:
        os.environ['MS_PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

    return True


def get_log_file_path(log_filename: str) -> Path:
    """Get the path for a log file.

    For frozen apps, logs go next to the executable.
    For development, logs go in the current directory.

    Args:
        log_filename: Name of the log file

    Returns:
        Path to the log file
    """
    if is_frozen():
        # Logs next to executable for easy access
        return get_executable_dir() / log_filename
    else:
        # Development - current directory
        return Path(log_filename)


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory: Directory path to ensure exists

    Returns:
        Path object for the directory

    Raises:
        OSError: If directory cannot be created
    """
    dir_path = Path(directory)

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {dir_path}")
        return dir_path
    except OSError as e:
        logger.error(f"Failed to create directory '{dir_path}': {e}")
        raise


def safe_path_join(*parts: Union[str, Path]) -> Path:
    """Safely join path components.

    Args:
        *parts: Path components to join

    Returns:
        Joined Path object
    """
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    return result


def get_resource_path(resource_name: str) -> Path:
    """Get path to a bundled resource file.

    For frozen apps, looks in _MEIPASS.
    For development, looks in current directory.

    Args:
        resource_name: Name of the resource file

    Returns:
        Path to the resource file
    """
    return get_base_path() / resource_name
