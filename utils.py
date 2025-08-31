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

def combine_all_reports(directory: Union[str, Path]) -> Optional[str]:
		"""Combine all reports by type into a single multi-sheet XLSX file.
		
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
				# Define all report types based on TABS configuration
				report_types = [
						"Student Usage",
						"Skill", 
						"Assignment",
						"Assessment",
						"Level Up Progress"
				]
				
				# Find all report files for each type
				reports_by_type = {}
				for report_type in report_types:
						# Use glob pattern to find files containing the report type
						pattern = f"*_{report_type}_*.xlsx"
						files = list(reports_directory.glob(pattern))
						if files:
								reports_by_type[report_type] = files
								logger.info(f"Found {len(files)} {report_type} reports")
				
				if not reports_by_type:
						logger.info("No reports found to combine")
						return None
				
				# Create a new workbook for combined reports
				combined_wb = Workbook()
				# Remove the default sheet
				combined_wb.remove(combined_wb.active)
				
				# Process each report type
				successful_sheets = 0
				
				for report_type, files in reports_by_type.items():
						try:
								logger.debug(f"Processing {report_type} reports")
								
								# Create a new sheet for this report type
								# Sanitize sheet name (Excel has restrictions on sheet names)
								sheet_name = report_type[:31]  # Excel sheet names max 31 chars
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
								
								# Process all files of this type and combine their data
								all_data = []
								headers_written = False
								
								for file_path in sorted(files):
										try:
												# Validate file exists and is readable
												if not file_path.exists() or file_path.stat().st_size == 0:
														logger.warning(f"File {file_path} is empty or doesn't exist, skipping")
														continue
												
												# Read the Excel file with error handling
												try:
														df = pd.read_excel(file_path, engine='openpyxl')
												except Exception as read_error:
														logger.error(f"Failed to read Excel file {file_path}: {read_error}")
														continue
												
												if df.empty:
														logger.warning(f"Excel file {file_path} contains no data, skipping")
														continue
												
												# Add a separator row with username if this isn't the first file
												if all_data:
														# Add separator row with username from filename
														username = file_path.stem.split('_')[0]
														separator_row = [f"--- {username} ---"] + [''] * (len(df.columns) - 1)
														all_data.append(separator_row)
												
												# Write headers only once
												if not headers_written:
														# Write column headers
														ws.append(list(df.columns))
														headers_written = True
												
												# Write the data rows
												for _, row in df.iterrows():
														# Handle potential None values in rows
														cleaned_row = [cell if pd.notna(cell) else '' for cell in row]
														all_data.append(cleaned_row)
														
										except Exception as e:
												logger.error(f"Error processing file {file_path}: {e}")
												continue
								
								# Write all collected data to the sheet
								if all_data:
										try:
												for row_data in all_data:
														ws.append(row_data)
												
												# Add summary rows for Student Usage sheet only
												if report_type == "Student Usage":
														try:
																# Calculate totals (excluding separator rows)
																total_students = 0
																total_listens = 0
																total_reads = 0
																total_quiz = 0
																
																# Process each data row (skip separator rows)
																for i, row_data in enumerate(all_data):
																		# Skip separator rows (they start with "---")
																		if isinstance(row_data[0], str) and row_data[0].startswith("---"):
																				continue
																		
																		# Count students (first column)
																		if len(row_data) > 0 and pd.notna(row_data[0]) and row_data[0] != '':
																				total_students += 1
																		
																		# Sum listens (6th column, index 5)
																		if len(row_data) > 5 and pd.notna(row_data[5]):
																				try:
																						total_listens += float(row_data[5])
																				except (ValueError, TypeError):
																						pass
																		
																		# Sum reads (7th column, index 6)
																		if len(row_data) > 6 and pd.notna(row_data[6]):
																				try:
																						total_reads += float(row_data[6])
																				except (ValueError, TypeError):
																						pass
																		
																		# Sum quiz (8th column, index 7)
																		if len(row_data) > 7 and pd.notna(row_data[7]):
																				try:
																						total_quiz += float(row_data[7])
																				except (ValueError, TypeError):
																						pass
																
																# Calculate grand total
																grand_total = total_listens + total_reads + total_quiz
																
																# Add empty row for spacing
																ws.append([])
																
																# Add summary rows
																summary_rows = [
																		["SUMMARY", "", "", "", "", "", "", ""],
																		["Total Students", total_students, "", "", "", "", "", ""],
																		["Total Listens", "", "", "", "", total_listens, "", ""],
																		["Total Reads", "", "", "", "", "", total_reads, ""],
																		["Total Quiz", "", "", "", "", "", "", total_quiz],
																		["GRAND TOTAL", "", "", "", "", grand_total, "", ""]
																]
																
																for summary_row in summary_rows:
																		ws.append(summary_row)
																
																logger.debug(f"Added summary rows to Student Usage sheet: Students={total_students}, Listens={total_listens}, Reads={total_reads}, Quiz={total_quiz}, Total={grand_total}")
																
														except Exception as summary_error:
																logger.debug(f"Error adding summary rows to Student Usage sheet: {summary_error}")
																# Continue without summary rows rather than failing
												
												# Auto-adjust column widths with error handling
												try:
														for column_cells in ws.columns:
																length = max(len(str(cell.value or '')) for cell in column_cells)
																ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
												except Exception as format_error:
														logger.debug(f"Error adjusting column widths for {report_type}: {format_error}")
														# Continue without column adjustment
												
												successful_sheets += 1
												logger.debug(f"Successfully added sheet for {report_type}")
												
										except Exception as write_error:
												logger.error(f"Error writing data to sheet for {report_type}: {write_error}")
												# Remove the sheet if writing failed
												combined_wb.remove(ws)
												continue
								
						except Exception as e:
								logger.error(f"Unexpected error processing {report_type} reports: {e}")
								continue
				
				if successful_sheets == 0:
						logger.error("No sheets could be created for the combined report")
						return None
				
				# Generate filename with timestamp
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				combined_filename = f"Combined_All_Reports_{timestamp}.xlsx"
				
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
				logger.info(f"Combined {successful_sheets} report type sheets into single file")
				
				return str(combined_file_path)
				
		except Exception as e:
				logger.error(f"Error combining reports: {e}")
				return None
