"""Client identification and UUID management.

This module handles generation, storage, and retrieval of a unique client ID
for log sharing and remote configuration lookups.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from path_helpers import get_executable_dir

logger = logging.getLogger(__name__)

CLIENT_ID_FILE = "client_id.json"


def generate_client_id() -> str:
    """Generate a new unique client ID.

    Returns:
        UUID string without dashes (32 characters)
    """
    return str(uuid4()).replace("-", "")


def get_client_id() -> str:
    """Get or create the client's unique ID.

    On first run, generates a UUID and saves it to client_id.json
    next to the executable. On subsequent runs, loads the existing ID.

    Returns:
        Client ID string (32-character hex)
    """
    client_id_path = get_executable_dir() / CLIENT_ID_FILE

    try:
        if client_id_path.exists():
            with open(client_id_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stored_id = data.get("client_id")
                if stored_id:
                    logger.debug(f"Loaded existing client ID: {stored_id[:8]}...")
                    return stored_id
                else:
                    logger.warning("client_id.json exists but has no client_id")
        else:
            logger.debug("No existing client ID file found")

        # Generate new client ID
        new_id = generate_client_id()

        # Save to file
        client_data = {
            "client_id": new_id,
            "generated_at": None  # Could add timestamp if needed
        }

        with open(client_id_path, "w", encoding="utf-8") as f:
            json.dump(client_data, f, indent=2)

        logger.info(f"Generated new client ID: {new_id[:8]}...")
        return new_id

    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error managing client ID file: {e}")
        # Fallback to a temporary ID for this session
        fallback_id = generate_client_id()
        logger.warning(f"Using fallback client ID: {fallback_id[:8]}...")
        return fallback_id


def get_client_id_for_display() -> dict:
    """Get client ID info for display in the UI.

    Returns a dict with the client ID and file path for showing
    to the user so they can share it with the developer.

    Returns:
        Dict with client_id and path keys
    """
    client_id_path = get_executable_dir() / CLIENT_ID_FILE
    return {
        "client_id": get_client_id(),
        "path": str(client_id_path)
    }
