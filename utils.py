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
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ResultsSheetMetrics:
    """Data class for storing results sheet metrics."""
    teachers: int = 0
    total_students: int = 0
    listens: int = 0
    reads: int = 0
    quiz: int = 0
    
    @property
    def total_activities(self) -> int:
        """Calculate total activities (Listens + Reads + Quiz)."""
        return self.listens + self.reads + self.quiz
    
    def add_user_metrics(self, user_data: pd.DataFrame) -> None:
        """Add metrics from a single user's data sheet.
        
        Args:
            user_data: DataFrame containing student usage data for one teacher
        """
        try:
            if user_data.empty:
                logger.debug("Empty dataframe provided for user metrics")
                return
            
            # Skip header rows that contain non-numeric data in first few rows
            data_start_idx = 0
            for idx in range(min(5, len(user_data))):  # Check first 5 rows
                row = user_data.iloc[idx]
                # If row has any numeric values, consider it data
                if any(pd.to_numeric(row, errors='coerce').notna()):
                    data_start_idx = idx
                    break
            
            # Use data from the detected starting point
            working_data = user_data.iloc[data_start_idx:].copy()
            
            if working_data.empty:
                logger.warning("No data rows found after header detection")
                return
            
            # Convert all columns to numeric, handling errors gracefully
            numeric_data = {}
            for i, col in enumerate(working_data.columns):
                try:
                    numeric_values = pd.to_numeric(working_data[col], errors='coerce')
                    # Only keep if at least some values are numeric
                    if not numeric_values.isna().all():
                        numeric_data[i] = numeric_values.fillna(0)  # Fill NaN with 0
                except Exception:
                    continue
            
            if not numeric_data:
                logger.warning("No numeric columns found in user data")
                return
            
            # Calculate metrics based on column positions (1-indexed from requirements)
            # Column 1 (index 0): Total Students - if numeric, sum values; otherwise count rows
            if 0 in numeric_data:
                first_col_sum = int(numeric_data[0].sum())
                self.total_students += first_col_sum
                logger.debug(f"Added {first_col_sum} students from column 1 (numeric sum)")
            else:
                # First column is not numeric (likely student names), count non-empty rows
                non_empty_rows = working_data.iloc[:, 0].dropna().shape[0]
                self.total_students += non_empty_rows
                logger.debug(f"Added {non_empty_rows} students from column 1 (row count)")
            
            # Column 6 (index 5): Listens  
            if 5 in numeric_data:
                listens_sum = int(numeric_data[5].sum())
                self.listens += listens_sum
                logger.debug(f"Added {listens_sum} listens from column 6")
            
            # Column 7 (index 6): Reads
            if 6 in numeric_data:
                reads_sum = int(numeric_data[6].sum())
                self.reads += reads_sum
                logger.debug(f"Added {reads_sum} reads from column 7")
            
            # Quiz calculation - look for columns containing "quiz" (case insensitive)
            quiz_total = 0
            for col_name in working_data.columns:
                if 'quiz' in str(col_name).lower():
                    try:
                        quiz_values = pd.to_numeric(working_data[col_name], errors='coerce').fillna(0)
                        quiz_sum = int(quiz_values.sum())
                        quiz_total += quiz_sum
                        logger.debug(f"Added {quiz_sum} quiz points from column '{col_name}'")
                    except Exception as e:
                        logger.debug(f"Error processing quiz column '{col_name}': {e}")
                        continue
            
            self.quiz += quiz_total
            
            # Increment teacher count only after successful processing
            self.teachers += 1
            
            logger.debug(f"Updated metrics - Teachers: {self.teachers}, Students: {self.total_students}, "
                        f"Listens: {self.listens}, Reads: {self.reads}, Quiz: {self.quiz}")
            
        except Exception as e:
            logger.error(f"Error adding user metrics: {e}")
            # Still increment teacher count even if data processing fails - they had a report
            self.teachers += 1
    
    def to_dict(self) -> Dict[str, List[Union[str, int]]]:
        """Convert metrics to dictionary format for Excel output.
        
        Returns:
            Dictionary with 'Metric' and 'Value' keys for creating DataFrame
        """
        return {
            'Metric': ['Teachers', 'Total Students', 'Listens', 'Reads', 'Quiz', 'Total'],
            'Value': [self.teachers, self.total_students, self.listens, self.reads, self.quiz, self.total_activities]
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"ResultsSheetMetrics(teachers={self.teachers}, "
                f"total_students={self.total_students}, listens={self.listens}, "
                f"reads={self.reads}, quiz={self.quiz}, total={self.total_activities})")

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

def combine_student_usage_reports_with_results(directory: Union[str, Path]) -> Optional[str]:
    """Combine all Student Usage reports into a single multi-sheet XLSX file with results summary.
    
    Args:
        directory: Path to the reports directory (can be relative or absolute)
        
    Returns:
        Path to the combined file if successful, None otherwise
    """
    import sys
    import os
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.styles import Font, Alignment, PatternFill
    
    # Handle both relative and absolute paths, with PyInstaller compatibility
    if os.path.isabs(str(directory)):
        # If absolute path, use as-is
        reports_directory = Path(directory)
    else:
        # For relative paths, resolve against the correct base directory
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            base_path = sys._MEIPASS
        else:
            # Running in development
            base_path = os.path.abspath('.')
        
        reports_directory = Path(base_path) / directory
    
    if not reports_directory.exists():
        logger.warning(f"Reports directory not found: {reports_directory}")
        return None
    
    try:
        # Find all Student Usage report files
        student_usage_files = list(reports_directory.glob('*_Student Usage*.xlsx'))
        
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
        
        # Initialize metrics collector
        metrics = ResultsSheetMetrics()
        
        # Process each user's report
        successful_sheets = 0
        user_dataframes = {}  # Store for results calculation
        
        for username, file_path in sorted(user_reports.items()):
            try:
                logger.debug(f"Processing report for user: {username}")
                
                # Validate file exists and is readable
                if not file_path.exists() or file_path.stat().st_size == 0:
                    logger.warning(f"File {file_path} is empty or doesn't exist, skipping user {username}")
                    continue
                
                # Read the Excel file with error handling
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except Exception as read_error:
                    logger.error(f"Failed to read Excel file {file_path}: {read_error}")
                    continue
                
                if df.empty:
                    logger.warning(f"Excel file {file_path} contains no data, skipping user {username}")
                    continue
                
                user_dataframes[username] = df
                
                # Add metrics from this user's data (this handles its own errors)
                try:
                    metrics.add_user_metrics(df)
                except Exception as metrics_error:
                    logger.error(f"Error calculating metrics for user {username}: {metrics_error}")
                    # Continue processing even if metrics fail
                
                # Create a new sheet for this user
                # Sanitize sheet name (Excel has restrictions on sheet names)
                sheet_name = username[:31]  # Excel sheet names max 31 chars
                # Remove invalid characters
                invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
                for char in invalid_chars:
                    sheet_name = sheet_name.replace(char, '_')
                
                # Ensure unique sheet name if sanitized name conflicts
                original_sheet_name = sheet_name
                counter = 1
                while sheet_name in [ws.title for ws in combined_wb.worksheets]:
                    sheet_name = f"{original_sheet_name[:28]}_{counter}"  # Leave room for counter
                    counter += 1
                
                ws = combined_wb.create_sheet(title=sheet_name)
                
                # Write the data to the sheet with error handling
                try:
                    for r in dataframe_to_rows(df, index=False, header=True):
                        # Handle potential None values in rows
                        cleaned_row = [cell if cell is not None else '' for cell in r]
                        ws.append(cleaned_row)
                except Exception as write_error:
                    logger.error(f"Error writing data to sheet for user {username}: {write_error}")
                    # Remove the sheet if writing failed
                    combined_wb.remove(ws)
                    continue
                
                # Auto-adjust column widths with error handling
                try:
                    for column_cells in ws.columns:
                        length = max(len(str(cell.value or '')) for cell in column_cells)
                        ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
                except Exception as format_error:
                    logger.debug(f"Error adjusting column widths for user {username}: {format_error}")
                    # Continue without column adjustment
                
                successful_sheets += 1
                logger.debug(f"Successfully added sheet for user: {username}")
                
            except Exception as e:
                logger.error(f"Unexpected error processing report for user {username}: {e}")
                continue
        
        if successful_sheets == 0:
            logger.error("No sheets could be created for the combined report")
            return None
        
        # Create the "results" summary sheet at the beginning
        try:
            logger.info("Creating results summary sheet")
            
            # Create results sheet as the first sheet
            results_ws = combined_wb.create_sheet(title="results", index=0)
            
            # Convert metrics to DataFrame for easier handling
            metrics_dict = metrics.to_dict()
            results_df = pd.DataFrame(metrics_dict)
            
            # Write headers with formatting
            results_ws['A1'] = 'Metric'
            results_ws['B1'] = 'Value'
            
            # Apply header formatting
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center")
            
            for cell in ['A1', 'B1']:
                results_ws[cell].font = header_font
                results_ws[cell].fill = header_fill
                results_ws[cell].alignment = header_alignment
            
            # Write data rows
            for idx, (metric, value) in enumerate(zip(metrics_dict['Metric'], metrics_dict['Value']), 2):
                results_ws[f'A{idx}'] = metric
                results_ws[f'B{idx}'] = value
            
            # Auto-adjust column widths for results sheet
            for column_cells in results_ws.columns:
                length = max(len(str(cell.value or '')) for cell in column_cells)
                results_ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 20)
            
            logger.info(f"results sheet created with metrics: Teachers={metrics.teachers}, "
                       f"Students={metrics.total_students}, Listens={metrics.listens}, "
                       f"Reads={metrics.reads}, Quiz={metrics.quiz}, Total={metrics.total_activities}")
            
        except Exception as e:
            logger.error(f"Error creating results sheet: {e}")
            # Continue without results sheet rather than failing completely
        
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
        logger.info(f"Combined {successful_sheets} user reports with results sheet into single file")
        
        return str(combined_file_path)
        
    except Exception as e:
        logger.error(f"Error combining Student Usage reports: {e}")
        return None

def combine_student_usage_reports(directory: Union[str, Path]) -> Optional[str]:
    """Combine all Student Usage reports into a single multi-sheet XLSX file.
    
    Args:
        directory: Path to the reports directory (can be relative or absolute)
        
    Returns:
        Path to the combined file if successful, None otherwise
    """
    import sys
    import os
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    # Handle both relative and absolute paths, with PyInstaller compatibility
    if os.path.isabs(str(directory)):
        # If absolute path, use as-is
        reports_directory = Path(directory)
    else:
        # For relative paths, resolve against the correct base directory
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            base_path = sys._MEIPASS
        else:
            # Running in development
            base_path = os.path.abspath('.')
        
        reports_directory = Path(base_path) / directory
    
    if not reports_directory.exists():
        logger.warning(f"Reports directory not found: {reports_directory}")
        return None
    
    try:
        # Find all Student Usage report files
        student_usage_files = list(reports_directory.glob('*_Student Usage*.xlsx'))
        
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
