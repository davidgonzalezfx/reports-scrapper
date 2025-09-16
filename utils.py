"""Utility functions for the reports scraper application."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import logging
from docx import Document

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
		import sys
		import os

		# Handle PyInstaller executable case
		if getattr(sys, 'frozen', False):
				# When running as executable, check both internal and external reports directories
				base_path = sys._MEIPASS
				external_dir = Path(os.path.join(os.path.dirname(sys.executable), str(directory)))
				internal_dir = Path(base_path) / directory

				all_files = []

				# Check external directory first (priority for user downloads)
				if external_dir.exists():
						try:
								files = [f.name for f in external_dir.glob('*.xlsx') if f.is_file()]
								all_files.extend(files)
								logger.debug(f"Found {len(files)} report files in external directory: {external_dir}")
						except OSError as e:
								logger.warning(f"Error reading external reports directory {external_dir}: {e}")

				# Check internal directory
				if internal_dir.exists():
						try:
								files = [f.name for f in internal_dir.glob('*.xlsx') if f.is_file()]
								all_files.extend(files)
								logger.debug(f"Found {len(files)} report files in internal directory: {internal_dir}")
						except OSError as e:
								logger.warning(f"Error reading internal reports directory {internal_dir}: {e}")

				# Remove duplicates and sort by name (newest first based on timestamp in filename)
				unique_files = list(set(all_files))
				unique_files.sort(reverse=True)

				logger.debug(f"Total found {len(unique_files)} unique report files")
				return unique_files
		else:
				# Running in development mode - use original logic
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

def update_docx_template(template_path: Union[str, Path], data: Dict[str, Any]):
    """Update a .docx template by replacing placeholders with data.

    Args:
        template_path: Path to the .docx template file.
        data: Dictionary with placeholder names as keys and their values.
    """
    try:
        template_path = Path(template_path)
        if not template_path.exists():
            logger.error(f"DOCX template not found: {template_path}")
            return

        doc = Document(template_path)

        # Replace in paragraphs
        for p in doc.paragraphs:
          for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            # Check if the placeholder exists in the paragraph text (including spaces)
            if placeholder in p.text:
              # Log placeholder information
              inline = p.runs
              # Join the runs into a single string to handle the case where the placeholder
              # may be split across multiple runs.
              full_text = ''.join(run.text for run in inline)

              if placeholder in full_text:
                # Now replace the placeholder in the full text (this will handle cases 
                # where the placeholder is split across multiple runs).
                new_full_text = full_text.replace(placeholder, str(value))

                # Rebuild the runs from the modified full text
                start = 0
                for run in inline:
                  end = start + len(run.text)
                  run.text = new_full_text[start:end]
                  start = end

                logger.debug(f"Replaced {placeholder} with {value} in paragraph")

        # Create a new filename for the updated document
        # Save to reports directory instead of template directory for better web interface access
        import sys
        import os

        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable - save to both internal and external reports directories
            base_path = sys._MEIPASS
            internal_reports_dir = Path(base_path) / 'reports'
            external_reports_dir = Path(os.path.dirname(sys.executable)) / 'reports'

            # Ensure directories exist
            internal_reports_dir.mkdir(parents=True, exist_ok=True)
            external_reports_dir.mkdir(parents=True, exist_ok=True)

            # Save to internal directory (where the app expects it)
            output_path = internal_reports_dir / f"Reporte Colegios.docx"
            doc.save(output_path)

            # Also copy to external directory for user access
            external_output_path = external_reports_dir / f"Reporte Colegios.docx"
            doc.save(external_output_path)

            logger.info(f"Saved updated document to internal: {output_path}")
            logger.info(f"Saved updated document to external: {external_output_path}")
        else:
            # Running in development - save to local reports directory
            reports_dir = Path('reports')
            reports_dir.mkdir(parents=True, exist_ok=True)
            output_path = reports_dir / f"Reporte Colegios.docx"
            doc.save(output_path)
            logger.info(f"Saved updated document to: {output_path}")
        logger.info(f"Successfully updated DOCX template: {template_path.name}")

    except Exception as e:
        logger.error(f"Failed to update DOCX template: {e}")

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
		from openpyxl.styles import PatternFill, Font, Alignment
		from openpyxl.formatting.rule import DataBarRule
		
		summary_data = None

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
				
				# Define styling for headers
				header_fill = PatternFill(start_color="D4E6F1", end_color="D4E6F1", fill_type="solid")
				header_font = Font(bold=True, color="000000")
				header_alignment = Alignment(horizontal="center", vertical="center")
				
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
								header_row_num = None
								
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
												
												# Write headers only once
												if not headers_written:
														# Write column headers
														ws.append(list(df.columns))
														header_row_num = ws.max_row
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
												
												# Apply header styling
												if header_row_num:
														try:
																for cell in ws[header_row_num]:
																		cell.fill = header_fill
																		cell.font = header_font
																		cell.alignment = header_alignment
														except Exception as style_error:
																logger.debug(f"Error applying header styling: {style_error}")
												
												# Add totals row for Student Usage sheet only - placed directly below data
												if report_type == "Student Usage":
														try:
																# Calculate totals from the actual data
																total_students = len(all_data)  # Count all data rows
																total_teachers = len(files)  # Count unique teachers/users (one file per teacher)
																total_listens = 0
																total_reads = 0
																total_quizzes = 0
																
																# Process each data row
																for row_data in all_data:
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
																		
																		# Sum quizzes (8th column, index 7)
																		if len(row_data) > 7 and pd.notna(row_data[7]):
																				try:
																						total_quizzes += float(row_data[7])
																				except (ValueError, TypeError):
																						pass
																
																# Calculate total activities
																total_activities = total_listens + total_reads + total_quizzes
																
																summary_data = {
																		"all_teachers": total_teachers,
																		"all_students": total_students,
																		"total_listen": int(total_listens),
																		"total_read": int(total_reads),
																		"total_quizzes": int(total_quizzes),
																		"total_activities": int(total_activities),
																}

																# Get the number of columns to create proper rows
																num_cols = len(df.columns) if 'df' in locals() else 8
																
																# Add empty row for spacing
																ws.append([''] * num_cols)
																
																# Create summary rows in columns A and B
																summary_rows = [
																		['Total Teachers', total_teachers],
																		['Total Students', total_students],
																		['Total Listens', int(total_listens)],
																		['Total Reads', int(total_reads)],
																		['Total Quizzes', int(total_quizzes)],
																		['Total', int(total_activities)]
																]
																
																# Add each summary row with empty cells for other columns
																for label, value in summary_rows:
																		row = [''] * num_cols
																		row[0] = label  # Column A
																		row[1] = value  # Column B
																		ws.append(row)
																		
																		# Apply styling to the summary row
																		row_num = ws.max_row
																		try:
																				# Style only columns A and B
																				ws[f'A{row_num}'].fill = header_fill
																				ws[f'A{row_num}'].font = header_font
																				ws[f'A{row_num}'].alignment = Alignment(horizontal="left", vertical="center")
																				
																				ws[f'B{row_num}'].fill = header_fill
																				ws[f'B{row_num}'].font = header_font
																				ws[f'B{row_num}'].alignment = Alignment(horizontal="right", vertical="center")
																		except Exception as style_error:
																				logger.debug(f"Error applying summary row styling: {style_error}")
																
																logger.debug(f"Added totals row to Student Usage sheet: Students={total_students}, Teachers={total_teachers}, Listens={total_listens}, Reads={total_reads}, Quizzes={total_quizzes}")
																
														except Exception as totals_error:
																logger.debug(f"Error adding totals row to Student Usage sheet: {totals_error}")
																# Continue without totals rather than failing
												
												# Auto-adjust column widths with error handling
												try:
														for column_cells in ws.columns:
																length = max(len(str(cell.value or '')) for cell in column_cells)
																ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
												except Exception as format_error:
														logger.debug(f"Error adjusting column widths for {report_type}: {format_error}")
														# Continue without column adjustment
												
												# Add visual data bars for Skill sheet column D
												if report_type == "Skill":
														try:
																# Find the range for column D with data (excluding header)
																if ws.max_row > 1:  # Check if we have data rows beyond header
																		# Column D is the 4th column
																		data_start_row = 2  # Start from row 2 (after header)
																		data_end_row = ws.max_row
																		
																		# Create range string for column D data
																		data_range = f"D{data_start_row}:D{data_end_row}"
																		
																		# Create data bar rule with blue color and custom settings
																		data_bar_rule = DataBarRule(
																				start_type='num', start_value=0,
																				end_type='num', end_value=100,
																				color="4472C4",  # Blue color matching Excel's default
																				showValue=True,   # Show the actual values
																				minLength=0,      # Minimum bar length
																				maxLength=100     # Maximum bar length
																		)
																		
																		# Apply the data bar rule to column D
																		ws.conditional_formatting.add(data_range, data_bar_rule)
																		
																		logger.debug(f"Added data bars to Skill sheet column D for range {data_range}")
														except Exception as bar_error:
																logger.debug(f"Error adding data bars to Skill sheet: {bar_error}")
																# Continue without data bars rather than failing
												
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
				
				# Update the DOCX template
				docx_template_path = Path(base_path) / 'original.docx'
				if summary_data:
						update_docx_template(docx_template_path, summary_data)

				return str(combined_file_path)
				
		except Exception as e:
				logger.error(f"Error combining reports: {e}")
				return None
