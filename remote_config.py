"""Remote configuration fetching with caching.

This module fetches configuration from a remote GitHub raw file and caches
it locally to avoid excessive network requests.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from path_helpers import get_executable_dir

logger = logging.getLogger(__name__)

# Configuration
REMOTE_CONFIG_URL = os.getenv(
    "REMOTE_CONFIG_URL",
    "https://raw.githubusercontent.com/davidgonzalezfx/reports-scrapper/main/remote_config.json"
)
CACHE_FILE = "remote_config_cache.json"
# Cache for 1 hour by default
CACHE_DURATION_HOURS = int(os.getenv("REMOTE_CONFIG_CACHE_HOURS", "1"))


def get_cache_path() -> Path:
    """Get the path to the local cache file.

    Returns:
        Path to cache file next to executable
    """
    return get_executable_dir() / CACHE_FILE


def is_cache_valid() -> bool:
    """Check if the cached config is still valid.

    Returns:
        True if cache exists and is not expired
    """
    cache_path = get_cache_path()

    if not cache_path.exists():
        return False

    try:
        # Check file modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry = mtime + timedelta(hours=CACHE_DURATION_HOURS)
        return datetime.now() < expiry
    except OSError as e:
        logger.warning(f"Error checking cache validity: {e}")
        return False


def fetch_remote_config() -> Optional[Dict[str, Any]]:
    """Fetch configuration from remote URL.

    Returns:
        Config dict or None if fetch fails
    """
    url = os.getenv("REMOTE_CONFIG_URL", REMOTE_CONFIG_URL)

    try:
        logger.debug(f"Fetching remote config from: {url}")
        request = Request(url)
        request.add_header("User-Agent", "ReportsScraper/1.0")

        with urlopen(request, timeout=10) as response:
            data = response.read().decode("utf-8")
            config = json.loads(data)
            logger.info("Successfully fetched remote config")
            return config

    except (URLError, HTTPError) as e:
        logger.warning(f"Failed to fetch remote config: {e}")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid JSON in remote config: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching remote config: {e}")
        return None


def save_cache(config: Dict[str, Any]) -> None:
    """Save configuration to local cache.

    Args:
        config: Configuration dict to cache
    """
    cache_path = get_cache_path()

    try:
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "config": config
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        logger.debug(f"Saved remote config to cache: {cache_path}")
    except OSError as e:
        logger.warning(f"Failed to save config cache: {e}")


def load_cache() -> Optional[Dict[str, Any]]:
    """Load configuration from local cache.

    Returns:
        Cached config dict or None if cache doesn't exist
    """
    cache_path = get_cache_path()

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        logger.debug("Loaded remote config from cache")
        return cache_data.get("config")
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load config cache: {e}")
        return None


def get_remote_config(force_refresh: bool = False) -> Dict[str, Any]:
    """Get remote configuration with caching.

    Tries to load from cache first. If cache is expired or force_refresh
    is True, fetches from remote URL.

    Args:
        force_refresh: Force fetching from remote even if cache is valid

    Returns:
        Configuration dict (empty dict if both cache and remote fail)
    """
    # Try cache first
    if not force_refresh and is_cache_valid():
        cached = load_cache()
        if cached:
            return cached

    # Fetch from remote
    remote = fetch_remote_config()
    if remote:
        save_cache(remote)
        return remote

    # Fallback to cache even if expired
    cached = load_cache()
    if cached:
        logger.info("Using expired cache as fallback")
        return cached

    logger.warning("No remote config available, using empty config")
    return {}


def is_log_sharing_enabled() -> bool:
    """Check if log sharing is globally enabled.

    Returns:
        True if log sharing is enabled, False otherwise
    """
    config = get_remote_config()

    # Default to disabled if not explicitly enabled
    enabled = config.get("log_sharing_enabled", False)

    logger.info(f"Log sharing globally enabled: {enabled}")
    return enabled


