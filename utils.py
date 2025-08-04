"""Utility functions for the reports scraper application."""

import json
import os
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_json(file_path: Union[str, Path], default: Any = None) -> Any:
    """Load JSON data from file with error handling."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.info(f"JSON file not found: {file_path}")
        return default
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"Successfully loaded JSON from {file_path}")
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return default

def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
    """Save data to JSON file with error handling."""
    file_path = Path(file_path)
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.debug(f"Successfully saved JSON to {file_path}")
        return True
    except (OSError, TypeError) as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False

def convert_csv_to_xlsx(csv_path: Union[str, Path], remove_csv: bool = True) -> Optional[str]:
    """Convert CSV file to XLSX format."""
    csv_path = Path(csv_path)
    xlsx_path = csv_path.with_suffix('.xlsx')
    
    try:
        logger.debug(f"Converting {csv_path} to XLSX")
        df = pd.read_csv(csv_path)
        df.to_excel(xlsx_path, index=False)
        
        logger.info(f"Successfully converted to XLSX: {xlsx_path.name}")
        
        if remove_csv:
            try:
                csv_path.unlink()
                logger.debug(f"Removed original CSV: {csv_path}")
            except OSError as e:
                logger.warning(f"Could not remove CSV {csv_path}: {e}")
        
        return str(xlsx_path)
        
    except Exception as e:
        logger.error(f"Failed to convert {csv_path} to XLSX: {e}")
        return None

def validate_filename(filename: str) -> bool:
    """Validate filename for security (prevent path traversal)."""
    if not filename:
        return False
    
    dangerous_patterns = ['..', '/', '\\']
    return not any(pattern in filename for pattern in dangerous_patterns)

def validate_user_data(user: Dict[str, Any]) -> bool:
    """Validate user data structure."""
    if not isinstance(user, dict):
        return False
    
    required_fields = ['username', 'password']
    return all(field in user and user[field] for field in required_fields)

def get_report_files(directory: Union[str, Path]) -> List[str]:
    """Get list of XLSX report files in directory."""
    directory = Path(directory)
    
    if not directory.exists():
        logger.warning(f"Reports directory not found: {directory}")
        return []
    
    try:
        files = [f.name for f in directory.glob('*.xlsx') if f.is_file()]
        files.sort(reverse=True)  # Sort newest first
        
        logger.debug(f"Found {len(files)} report files")
        return files
        
    except OSError as e:
        logger.error(f"Error reading reports directory: {e}")
        return []
