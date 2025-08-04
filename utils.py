"""Utility functions for the reports scraper application.

This module provides common utility functions used across different
components of the application.
"""

import json
import os
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd

from config import setup_logging, REPORTS_DIR

logger = setup_logging(__name__, 'utils.log')

class FileManager:
    """File management utilities."""
    
    @staticmethod
    def load_json(file_path: Union[str, Path], default: Any = None) -> Any:
        """Load JSON data from file with error handling.
        
        Args:
            file_path: Path to JSON file
            default: Default value to return if file doesn't exist or is invalid
            
        Returns:
            Parsed JSON data or default value
        """
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
    
    @staticmethod
    def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
        """Save data to JSON file with error handling.
        
        Args:
            data: Data to save
            file_path: Path to save file
            indent: JSON indentation level
            
        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.debug(f"Successfully saved JSON to {file_path}")
            return True
        except (OSError, TypeError) as e:
            logger.error(f"Failed to save JSON to {file_path}: {e}")
            return False
    
    @staticmethod
    def ensure_directory(directory: Union[str, Path]) -> bool:
        """Ensure directory exists, create if necessary.
        
        Args:
            directory: Directory path
            
        Returns:
            True if directory exists or was created, False otherwise
        """
        directory = Path(directory)
        
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False
    
    @staticmethod
    def clean_directory(directory: Union[str, Path], pattern: str = "*") -> int:
        """Clean files from directory matching pattern.
        
        Args:
            directory: Directory to clean
            pattern: File pattern to match (default: all files)
            
        Returns:
            Number of files removed
        """
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0
        
        removed_count = 0
        try:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed file: {file_path}")
            
            if removed_count > 0:
                logger.info(f"Cleaned {removed_count} files from {directory}")
            return removed_count
            
        except OSError as e:
            logger.error(f"Error cleaning directory {directory}: {e}")
            return removed_count

class DataProcessor:
    """Data processing utilities."""
    
    @staticmethod
    def convert_csv_to_xlsx(csv_path: Union[str, Path], remove_csv: bool = True) -> Optional[Path]:
        """Convert CSV file to XLSX format.
        
        Args:
            csv_path: Path to CSV file
            remove_csv: Whether to remove original CSV file
            
        Returns:
            Path to XLSX file if successful, None otherwise
        """
        csv_path = Path(csv_path)
        xlsx_path = csv_path.with_suffix('.xlsx')
        
        try:
            logger.debug(f"Converting {csv_path} to XLSX")
            df = pd.read_csv(csv_path)
            df.to_excel(xlsx_path, index=False)
            
            logger.info(f"Successfully converted to XLSX: {xlsx_path.name}")
            
            # Remove original CSV if requested
            if remove_csv:
                try:
                    csv_path.unlink()
                    logger.debug(f"Removed original CSV: {csv_path}")
                except OSError as e:
                    logger.warning(f"Could not remove CSV {csv_path}: {e}")
            
            return xlsx_path
            
        except Exception as e:
            logger.error(f"Failed to convert {csv_path} to XLSX: {e}")
            return None
    
    @staticmethod
    def create_zip_archive(files: List[Union[str, Path]], zip_name: str = None) -> Optional[Path]:
        """Create a ZIP archive from a list of files.
        
        Args:
            files: List of file paths to include in archive
            zip_name: Name for the ZIP file (auto-generated if None)
            
        Returns:
            Path to created ZIP file if successful, None otherwise
        """
        if not files:
            logger.warning("No files provided for ZIP archive")
            return None
        
        if zip_name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_name = f'reports_{timestamp}.zip'
        
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        zip_path = Path(temp_zip.name)
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    file_path = Path(file_path)
                    if file_path.exists() and file_path.is_file():
                        zipf.write(file_path, file_path.name)
                        logger.debug(f"Added {file_path.name} to ZIP")
            
            logger.info(f"Created ZIP archive: {zip_name} with {len(files)} files")
            return zip_path
            
        except Exception as e:
            logger.error(f"Failed to create ZIP archive: {e}")
            # Clean up failed zip file
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except OSError:
                    pass
            return None

class ValidationUtils:
    """Validation utilities."""
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for security (prevent path traversal).
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if filename is safe, False otherwise
        """
        if not filename:
            return False
        
        # Check for path traversal attempts
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(pattern in filename for pattern in dangerous_patterns)
    
    @staticmethod
    def validate_user_data(user: Dict[str, Any]) -> bool:
        """Validate user data structure.
        
        Args:
            user: User dictionary to validate
            
        Returns:
            True if user data is valid, False otherwise
        """
        if not isinstance(user, dict):
            return False
        
        required_fields = ['username', 'password']
        return all(field in user and user[field] for field in required_fields)
    
    @staticmethod
    def validate_config_data(config: Dict[str, Any]) -> bool:
        """Validate configuration data structure.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if config is valid, False otherwise
        """
        if not isinstance(config, dict):
            return False
        
        # Check for required keys
        if 'date_filter' not in config or 'tabs' not in config:
            return False
        
        # Validate tabs structure
        tabs = config.get('tabs', {})
        if not isinstance(tabs, dict):
            return False
        
        return True

class ReportUtils:
    """Report-specific utilities."""
    
    @staticmethod
    def get_report_files(directory: Union[str, Path] = None) -> List[Path]:
        """Get list of report files in directory.
        
        Args:
            directory: Directory to search (defaults to REPORTS_DIR)
            
        Returns:
            List of report file paths, sorted by modification time (newest first)
        """
        if directory is None:
            directory = REPORTS_DIR
        
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Reports directory not found: {directory}")
            return []
        
        try:
            # Get all XLSX files
            files = [f for f in directory.glob('*.xlsx') if f.is_file()]
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            logger.debug(f"Found {len(files)} report files")
            return files
            
        except OSError as e:
            logger.error(f"Error reading reports directory: {e}")
            return []
    
    @staticmethod
    def generate_report_summary(files: List[Path]) -> Dict[str, Any]:
        """Generate summary information about report files.
        
        Args:
            files: List of report file paths
            
        Returns:
            Dictionary with summary information
        """
        if not files:
            return {
                'total_files': 0,
                'total_size': 0,
                'latest_file': None,
                'oldest_file': None
            }
        
        total_size = sum(f.stat().st_size for f in files if f.exists())
        
        # Sort by modification time
        sorted_files = sorted(files, key=lambda x: x.stat().st_mtime)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'latest_file': sorted_files[-1].name if sorted_files else None,
            'oldest_file': sorted_files[0].name if sorted_files else None,
            'latest_modified': datetime.fromtimestamp(sorted_files[-1].stat().st_mtime) if sorted_files else None
        }