"""Log uploader for GitHub Issues.

This module handles uploading log files and diagnostic information
to GitHub Issues when enabled via remote configuration.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from path_helpers import get_log_file_path, get_executable_dir
from client_id import get_client_id

logger = logging.getLogger(__name__)

# GitHub configuration
# The token can be provided via:
# 1. Runtime env var GITHUB_LOG_TOKEN (for development/testing)
# 2. Built-in token from _build_token.py (baked at build time)
# 3. Build-time env var BUILT_IN_GITHUB_TOKEN (fallback)
GITHUB_TOKEN = os.getenv("GITHUB_LOG_TOKEN", "")

# Try to load built-in token from _build_token.py (created at build time)
if not GITHUB_TOKEN:
    try:
        from _build_token import BUILT_IN_GITHUB_TOKEN
        GITHUB_TOKEN = BUILT_IN_GITHUB_TOKEN
    except ImportError:
        # No built-in token available
        pass

# Fallback to build-time env var
if not GITHUB_TOKEN:
    GITHUB_TOKEN = os.getenv("BUILT_IN_GITHUB_TOKEN", "")

GITHUB_REPO = os.getenv("GITHUB_LOG_REPO", "")  # format: username/repo-name
GITHUB_API_BASE = "https://api.github.com"

# Environment variable override for testing (bypass GitHub API)
TEST_MODE = os.getenv("LOG_UPLOADER_TEST_MODE", "false").lower() == "true"


def get_github_headers() -> dict:
    """Get headers for GitHub API requests.

    Returns:
        Dict with appropriate headers
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ReportsScraper-LogUploader/1.0"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def read_log_file(log_path: Path) -> str:
    """Read log file contents.

    Args:
        log_path: Path to log file

    Returns:
        File contents or empty string if file doesn't exist
    """
    try:
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    except OSError as e:
        logger.warning(f"Error reading log file {log_path}: {e}")
        return ""


def truncate_log(content: str, max_lines: int = 500) -> str:
    """Truncate log content to avoid hitting GitHub size limits.

    Args:
        content: Full log content
        max_lines: Maximum number of lines to keep

    Returns:
        Truncated content with indicator if cut off
    """
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return content

    truncated = "\n".join(lines[-max_lines:])
    return f"... (truncated, showing last {max_lines} lines) ...\n\n{truncated}"


def collect_log_info() -> dict:
    """Collect all relevant log and diagnostic information.

    Returns:
        Dict with log contents and metadata
    """
    client_id = get_client_id()

    logs = {
        "app_log": read_log_file(get_log_file_path("app.log")),
        "scraper_log": read_log_file(get_log_file_path("scraper.log")),
    }

    # Try to read config for diagnostics
    config_path = get_executable_dir() / "scraper_config.json"
    config_info = None
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            # Sanitize config - remove sensitive info
            config_info = {
                "institution_name": config_data.get("institution_name", "Unknown"),
                "date_filter": config_data.get("date_filter", "Unknown"),
                "products_filter": config_data.get("products_filter", "Unknown"),
                "skill_filter": config_data.get("skill_filter", "Unknown"),
                "has_users": False  # Will check below
            }
        except Exception as e:
            logger.warning(f"Error reading config for diagnostics: {e}")

    # Check if users are configured
    users_path = get_executable_dir() / "users.json"
    if users_path.exists():
        try:
            with open(users_path, "r", encoding="utf-8") as f:
                users = json.load(f)
            if config_info:
                config_info["has_users"] = len(users) > 0
                config_info["user_count"] = len(users)
        except Exception:
            pass

    return {
        "client_id": client_id,
        "timestamp": datetime.now().isoformat(),
        "logs": logs,
        "config": config_info
    }


def format_issue_body(log_info: dict, error_message: Optional[str] = None) -> str:
    """Format the GitHub Issue body.

    Args:
        log_info: Collected log information
        error_message: Optional error message that triggered the upload

    Returns:
        Formatted markdown for the issue body
    """
    client_id = log_info["client_id"]
    timestamp = log_info["timestamp"]

    body = f"""## Automated Log Upload

**Client ID**: `{client_id[:8]}...{client_id[-8:]}`
**Timestamp**: {timestamp}
**Error Message**: {error_message or "None - scheduled upload"}

---

## Configuration

"""

    if log_info.get("config"):
        cfg = log_info["config"]
        body += f"""
- **Institution**: {cfg.get('institution_name', 'Unknown')}
- **Date Filter**: {cfg.get('date_filter', 'Unknown')}
- **Products Filter**: {cfg.get('products_filter', 'Unknown')}
- **Skill Filter**: {cfg.get('skill_filter', 'Unknown')}
- **Users Configured**: {cfg.get('user_count', 0)}
"""
    else:
        body += "\n*Configuration information unavailable*\n"

    # App Log
    app_log = log_info["logs"]["app_log"]
    if app_log:
        body += "\n## App Log\n```\n"
        body += truncate_log(app_log, 300)
        body += "\n```\n\n"
    else:
        body += "\n## App Log\n*No app log available*\n"

    # Scraper Log
    scraper_log = log_info["logs"]["scraper_log"]
    if scraper_log:
        body += "\n## Scraper Log\n```\n"
        body += truncate_log(scraper_log, 500)
        body += "\n```\n"
    else:
        body += "\n## Scraper Log\n*No scraper log available*\n"

    body += "\n---\n*This issue was automatically created by the Reports Scraper*"

    return body


def create_github_issue(title: str, body: str, labels: Optional[List[str]] = None) -> Optional[str]:
    """Create a GitHub Issue.

    Args:
        title: Issue title
        body: Issue body in markdown
        labels: Optional list of labels to add

    Returns:
        Issue URL if successful, None otherwise
    """
    if not GITHUB_REPO:
        logger.error("GITHUB_LOG_REPO not configured")
        return None

    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/issues"

    payload = {
        "title": title,
        "body": body
    }
    if labels:
        payload["labels"] = labels

    try:
        request_data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=request_data, headers=get_github_headers(), method="POST")

        with urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            issue_url = response_data.get("html_url")
            issue_number = response_data.get("number")
            logger.info(f"Created GitHub Issue #{issue_number}: {issue_url}")
            return issue_url

    except HTTPError as e:
        logger.error(f"GitHub API error: {e.code} - {e.reason}")
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            logger.error(f"Error details: {error_body}")
        except Exception:
            pass
        return None
    except (URLError, OSError) as e:
        logger.error(f"Network error creating GitHub Issue: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating GitHub Issue: {e}")
        return None


def upload_logs(error_message: Optional[str] = None) -> bool:
    """Upload logs to GitHub Issue.

    Only uploads if log sharing is globally enabled via remote config.
    Requires GITHUB_LOG_TOKEN and GITHUB_LOG_REPO environment variables.

    Args:
        error_message: Optional error message that triggered the upload

    Returns:
        True if upload was successful, False otherwise
    """
    # Check if feature is enabled globally
    from remote_config import is_log_sharing_enabled

    if not is_log_sharing_enabled():
        logger.info("Log sharing not enabled globally")
        return False

    # Check GitHub configuration
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.warning("GitHub logging not configured (missing GITHUB_LOG_TOKEN or GITHUB_LOG_REPO)")
        return False

    client_id = get_client_id()

    # Test mode - just log without creating issue
    if TEST_MODE:
        logger.info("TEST MODE: Would upload logs to GitHub")
        log_info = collect_log_info()
        logger.debug(f"Test log info: {json.dumps({'client_id': log_info['client_id'], 'timestamp': log_info['timestamp']})}")
        return True

    # Collect and upload
    try:
        log_info = collect_log_info()
        body = format_issue_body(log_info, error_message)

        # Create title with client ID and timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = f"Log Upload - Client {client_id[:8]}... - {timestamp}"

        labels = ["automated-log", f"client-{client_id[:8]}"]
        if error_message:
            labels.append("error")

        issue_url = create_github_issue(title, body, labels)

        if issue_url:
            logger.info(f"Logs successfully uploaded: {issue_url}")
            return True
        else:
            logger.warning("Failed to upload logs to GitHub")
            return False

    except Exception as e:
        logger.error(f"Error during log upload: {e}")
        return False


def is_configured() -> bool:
    """Check if the log uploader is properly configured.

    Returns:
        True if GITHUB_LOG_TOKEN and GITHUB_LOG_REPO are set
    """
    return bool(GITHUB_TOKEN and GITHUB_REPO)
