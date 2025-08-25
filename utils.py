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

def combine_student_usage_reports(directory: Union[str, Path]) -> Optional[str]:
    """Combine all Student Usage reports into a single multi-sheet XLSX file.
    
    Args:
        directory: Path to the reports directory
        
    Returns:
        Path to the combined file if successful, None otherwise
    """
    import sys
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    directory = Path(directory)
    
    if not directory.exists():
        logger.warning(f"Reports directory not found: {directory}")
        return None
    
    try:
        # Find all Student Usage report files
        student_usage_files = list(directory.glob('*_Student Usage*.xlsx'))
        
        if not student_usage_files:
            logger.info("No Student Usage reports found to combine")
            return None
        
        logger.info(f"Found {len(student_usage_files)} Student Usage reports to combine")
        
        # Group files by username
        user_reports = {}
        for file_path in student_usage_files:
            filename = file_path.name
            # Extract username from filename (format: username_Student Usage Report.xlsx)
            if '_' in filename:
                username = filename.split('_')[0]
                user_reports[username] = file_path
            else:
                logger.warning(f"Could not extract username from filename: {filename}")
        
        if not user_reports:
            logger.warning("No valid Student Usage reports found to combine")
            return None
        
        # Create a new workbook for combined reports
        combined_wb = Workbook()
        # Remove the default sheet
        combined_wb.remove(combined_wb.active)
        
        # Process each user's report
        successful_sheets = 0
        for username, file_path in sorted(user_reports.items()):
            try:
                logger.debug(f"Processing report for user: {username}")
                
                # Read the Excel file
                df = pd.read_excel(file_path, engine='openpyxl')
                
                # Create a new sheet for this user
                # Sanitize sheet name (Excel has restrictions on sheet names)
                sheet_name = username[:31]  # Excel sheet names max 31 chars
                # Remove invalid characters
                invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
                for char in invalid_chars:
                    sheet_name = sheet_name.replace(char, '_')
                
                ws = combined_wb.create_sheet(title=sheet_name)
                
                # Write the data to the sheet
                for r in dataframe_to_rows(df, index=False, header=True):
                    ws.append(r)
                
                # Auto-adjust column widths
                for column_cells in ws.columns:
                    length = max(len(str(cell.value or '')) for cell in column_cells)
                    ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
                
                successful_sheets += 1
                logger.debug(f"Successfully added sheet for user: {username}")
                
            except Exception as e:
                logger.error(f"Error processing report for user {username}: {e}")
                continue
        
        if successful_sheets == 0:
            logger.error("No sheets could be created for the combined report")
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined_filename = f"Combined_Student_Usage_{timestamp}.xlsx"
        
        # Determine the correct path based on whether running as frozen executable
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')
        
        reports_dir_path = Path(base_path) / 'reports'
        combined_file_path = reports_dir_path / combined_filename
        
        # Save the combined workbook
        combined_wb.save(combined_file_path)
        logger.info(f"Successfully created combined report: {combined_filename}")
        logger.info(f"Combined {successful_sheets} user reports into single file")
        
        return str(combined_file_path)
        
    except Exception as e:
        logger.error(f"Error combining Student Usage reports: {e}")
        return None
