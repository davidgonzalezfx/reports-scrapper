"""Flask web application for reports scraping management."""

from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify, send_file
import os
import threading
import logging
import webbrowser
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from waitress import serve
import sys

from utils import load_json, save_json, validate_filename, validate_user_data, get_report_files, get_school_summary, get_classroom_summaries, get_reading_skills_data, get_top_readers_per_classroom, get_level_up_progress_data

# Constants
USERS_FILE = 'users.json'
REPORTS_DIR = 'reports'
CONFIG_FILE = 'scraper_config.json'
DATE_FILTERS = ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
PRODUCTS_FILTERS = ["All", "Raz-Plus", "Español", "Science A-Z", "Writing A-Z", "Vocabulary A-Z", "Foundations A-Z"]
TABS = [
		{"name": "Student Usage", "default": True},
		{"name": "Skill", "default": True},
		{"name": "Assignment", "default": True},
		{"name": "Assessment", "default": True},
		{"name": "Level Up Progress", "default": True},
]

def get_spanish_month(month: int) -> str:
	"""Convert month number to Spanish month name."""
	months = {
			1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
			7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
	}
	return months.get(month, "Enero")

def get_date_range_string(date_filter: str) -> str:
	"""Generate date range string based on selected filter."""
	today = datetime.now()

	if date_filter == "Today":
			start_date = end_date = today
			return f"{start_date.day:02d} {get_spanish_month(start_date.month)} {start_date.year}"
	elif date_filter == "Last 7 Days":
			end_date = today
			start_date = today - timedelta(days=7)
	elif date_filter == "Last 30 Days":
			end_date = today
			start_date = today - timedelta(days=30)
	elif date_filter == "Last 90 Days":
			end_date = today
			start_date = today - timedelta(days=90)
	elif date_filter == "Last Year":
			end_date = today
			start_date = today - timedelta(days=365)
	else:
			start_date = end_date = today

	start_str = f"{start_date.day:02d} {get_spanish_month(start_date.month)} {start_date.year}"
	end_str = f"{end_date.day:02d} {get_spanish_month(end_date.month)} {end_date.year}"
	return f"{start_str} - {end_str}"

def get_subtitle_string(date_filter: str) -> str:
	"""Generate subtitle string based on selected filter."""
	today = datetime.now()

	if date_filter == "Today":
			return f"{get_spanish_month(today.month)} {today.year}"
	elif date_filter == "Last 7 Days":
			end_date = today
			start_date = today - timedelta(days=7)
	elif date_filter == "Last 30 Days":
			end_date = today
			start_date = today - timedelta(days=30)
	elif date_filter == "Last 90 Days":
			end_date = today
			start_date = today - timedelta(days=90)
	elif date_filter == "Last Year":
			end_date = today
			start_date = today - timedelta(days=365)
	else:
			start_date = end_date = today

	if start_date.year == end_date.year:
			if start_date.month == end_date.month:
					return f"{get_spanish_month(start_date.month)} {start_date.year}"
			else:
					return f"{get_spanish_month(start_date.month)} - {get_spanish_month(end_date.month)} {end_date.year}"
	else:
			return f"{get_spanish_month(start_date.month)} {start_date.year} - {get_spanish_month(end_date.month)} {end_date.year}"

# Configure logging
logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
				logging.FileHandler('app.log'),
				logging.StreamHandler()
		]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

class AppState:
		"""Application state management."""
		
		def __init__(self):
				self.download_in_progress = False
				self._lock = threading.Lock()
				self.notifications = []  # Store notifications during scraping
		
		def set_download_status(self, status: bool) -> None:
				"""Thread-safe setter for download status."""
				with self._lock:
						self.download_in_progress = status
		
		def get_download_status(self) -> bool:
				"""Thread-safe getter for download status."""
				with self._lock:
						return self.download_in_progress
		
		def add_notification(self, message: str, type: str = 'warning') -> None:
				"""Thread-safe method to add a notification."""
				with self._lock:
						self.notifications.append({
								'message': message,
								'type': type,
								'timestamp': datetime.now().isoformat()
						})
						logger.info(f"Added notification: {type} - {message}")
		
		def get_notifications(self) -> List[Dict[str, str]]:
				"""Thread-safe getter for notifications."""
				with self._lock:
						return self.notifications.copy()
		
		def clear_notifications(self) -> None:
				"""Thread-safe method to clear all notifications."""
				with self._lock:
						self.notifications = []
						logger.info("Cleared all notifications")

app_state = AppState()

def save_config(config_data: Dict[str, Any]) -> None:
		"""Save configuration data to file."""
		if not save_json(config_data, CONFIG_FILE):
				raise OSError("Failed to save configuration")
		logger.info("Configuration saved successfully")

def load_config() -> Dict[str, Any]:
		"""Load configuration from file with fallback to defaults."""
		default_config = {
				"date_filter": DATE_FILTERS[0], 
				"products_filter": PRODUCTS_FILTERS[0],
				"tabs": {tab["name"]: tab["default"] for tab in TABS}
		}
		
		config = load_json(CONFIG_FILE, default_config)
		if config == default_config:
				logger.info("Using default configuration")
		else:
				logger.info("Configuration loaded successfully")
		return config

def get_mock_report_data() -> Dict[str, Any]:
		"""Generate mock data for the report presentation."""

		# Load configuration to get selected date filter
		config = load_config()
		date_filter = config.get('date_filter', DATE_FILTERS[0])

		# Compute dynamic date strings based on selected filter
		date_range = get_date_range_string(date_filter)
		subtitle = get_subtitle_string(date_filter)

		# Get real summary data from reports
		summary = get_school_summary(REPORTS_DIR)

		# Get real classroom data from reports
		classroom_summaries = get_classroom_summaries(REPORTS_DIR)

		# Get real reading skills data from reports
		reading_skills_data = get_reading_skills_data(REPORTS_DIR)

		# Get real level up progress data from reports
		level_up_progress_data = get_level_up_progress_data(REPORTS_DIR)

		# Get real top readers data from reports
		top_readers_data = get_top_readers_per_classroom(REPORTS_DIR)

		# Load institution name from scraper config
		scraper_config = load_json(CONFIG_FILE, {})
		institution_name = scraper_config.get('institution_name', 'Unidad Educativa')

		return {
				# Slide 1 data
				'report_title': 'REPORTE DE USO',
				'institution': institution_name,
				'date_range': date_range,
				'logos': [
						{'icon': 'school', 'text': 'b1 tech'},
						{'icon': 'menu_book', 'text': 'Learning A-Z'},
						{'icon': 'analytics', 'text': 'Raz-Kids'}
				],

				# Slide 2 data
				'school_overview': {
						'title': 'School General Overview',
						'subtitle': subtitle,
						'stats': [
								{'number': str(summary['all_teachers']) if summary else '2500', 'label': 'Docentes'},
								{'number': str(summary['all_students']) if summary else '2500', 'label': 'Estudiantes'}
						],
						'activities': [
								{'number': str(summary['total_listen']) if summary else '1500', 'name': 'Listen'},
								{'number': str(summary['total_read']) if summary else '1800', 'name': 'Read'},
								{'number': str(summary['total_quizzes']) if summary else '1900', 'name': 'Quiz'}
						],
						'total_activities': f"{summary['total_activities']:,}" if summary else '15,682',
						'activity_descriptions': [
								{'icon': 'headphones', 'text': 'Listen: Número de audiciones completadas'},
								{'icon': 'menu_book', 'text': 'Read: Número de lecturas completadas'},
								{'icon': 'quiz', 'text': 'Quiz: Número de cuestionarios completados'}
						],
						'chart_data': [
								round(summary['total_listen'] / summary['total_activities'] * 100, 1) if summary and summary['total_activities'] > 0 else 28.8,
								round(summary['total_read'] / summary['total_activities'] * 100, 1) if summary and summary['total_activities'] > 0 else 34.6,
								round(summary['total_quizzes'] / summary['total_activities'] * 100, 1) if summary and summary['total_activities'] > 0 else 36.5
						]
				},

				# Slide 3 data
				'detailed_activities': {
						'title': 'Detalle Total Actividades',
						'subtitle': subtitle,
						'activity_summary': [
								{'icon': 'headphones', 'number': str(int(sum(c['listen'] for c in classroom_summaries))) if classroom_summaries else '0', 'name': 'Listen'},
								{'icon': 'menu_book', 'number': str(int(sum(c['read'] for c in classroom_summaries))) if classroom_summaries else '0', 'name': 'Read'},
								{'icon': 'quiz', 'number': str(int(sum(c['quiz'] for c in classroom_summaries))) if classroom_summaries else '0', 'name': 'Quiz'}
						],
						'classrooms': [
								{
										'name': classroom['name'],
										'students': classroom['students'],
										'students_used': classroom.get('students_used', 0),
										'usage': classroom['usage'],
										'listen': int(classroom['listen']),
										'read': int(classroom['read']),
										'quiz': int(classroom['quiz']),
										'interactivity': int(classroom['interactivity']),
										'practice_recording': int(classroom['practice_recording'])
								}
								for classroom in (classroom_summaries if classroom_summaries else [])
						],
						'total': {
								'students': sum(c['students'] for c in classroom_summaries) if classroom_summaries else 0,
								'students_used': sum(c.get('students_used', 0) for c in classroom_summaries) if classroom_summaries else 0,
								'usage': round(sum(c['usage'] * c['students'] for c in classroom_summaries) / sum(c['students'] for c in classroom_summaries), 1) if classroom_summaries and sum(c['students'] for c in classroom_summaries) > 0 else 0,
								'listen': int(sum(c['listen'] for c in classroom_summaries)) if classroom_summaries else 0,
								'read': int(sum(c['read'] for c in classroom_summaries)) if classroom_summaries else 0,
								'quiz': int(sum(c['quiz'] for c in classroom_summaries)) if classroom_summaries else 0,
								'interactivity': int(sum(c['interactivity'] for c in classroom_summaries)) if classroom_summaries else 0,
								'practice_recording': int(sum(c['practice_recording'] for c in classroom_summaries)) if classroom_summaries else 0
						}
				},

				# Slide 4 data (reading skills from reports)
				'reading_skills': reading_skills_data if reading_skills_data else [],

				# Slide for level up progress
				'level_up_progress': level_up_progress_data if level_up_progress_data else [],

				# Slide 5 data
				'top_readers': {
						'title': 'Top Lectores por Aula',
						'subtitle': subtitle,
						'classrooms': top_readers_data if top_readers_data else []
				}
		}

def load_users() -> List[Dict[str, str]]:
		"""Load users from file with fallback to empty list."""
		users = load_json(USERS_FILE, [])
		logger.info(f"Loaded {len(users)} users successfully")
		return users

def save_users(users: List[Dict[str, str]]) -> None:
		"""Save users to file."""
		if not save_json(users, USERS_FILE):
				raise OSError("Failed to save users")
		logger.info(f"Saved {len(users)} users successfully")

def monitor_scraper_logs() -> None:
		"""Monitor scraper logs for supplementary information.
		
		Note: Critical errors are now handled directly through ScraperResult.
		This function now primarily captures supplementary log information.
		"""
		import time
		import os
		
		log_file = 'app.log'
		if not os.path.exists(log_file):
				return
		
		# Track last position in file
		last_position = 0
		
		while app_state.get_download_status():
				try:
						with open(log_file, 'r', encoding='utf-8') as f:
								f.seek(last_position)
								new_lines = f.readlines()
								last_position = f.tell()
								
								# Process any supplementary log messages if needed
								# Most error handling is now done through ScraperResult
								
				except Exception as e:
						logger.debug(f"Error monitoring logs: {e}")
				
				time.sleep(2)  # Check less frequently since primary errors come from ScraperResult

def run_scraper() -> None:
		"""Execute the scraper directly by importing and calling the scraper module."""
		try:
				app_state.set_download_status(True)
				app_state.clear_notifications()  # Clear previous notifications
				logger.info("Starting scraper process")
				
				# Start log monitoring in a separate thread
				monitor_thread = threading.Thread(target=monitor_scraper_logs, daemon=True)
				monitor_thread.start()
				
				users = load_users()
				if not users:
						logger.warning("No users found, scraper may not function properly")
						app_state.add_notification("No users configured for scraping", 'warning')
				
				# Import scraper module and call directly
				try:
						from scraper import run_scraper_for_users, ScraperResult
						result: ScraperResult = run_scraper_for_users(USERS_FILE, verbose=False)
						
						# Process the result and add appropriate notifications
						if result.success:
								logger.info("Scraper completed successfully")
								if result.users_processed < result.total_users:
										# Partial success - some users had errors
										app_state.add_notification(
												f"Scraper completed: {result.users_processed}/{result.total_users} users successful",
												'warning'
										)
								else:
										# Complete success
										app_state.add_notification(
												f"All {result.users_processed} users processed successfully",
												'success'
										)
						else:
								logger.error("Scraper failed - no users processed successfully")
								# Get detailed error information
								error_summary = result.get_error_summary()
								app_state.add_notification(error_summary, 'error')
						
						# Add individual user errors as separate notifications for visibility
						for user_result in result.user_results:
								if not user_result.success:
										if user_result.error_type == 'product_access':
												# Priority notification for product access errors
												app_state.add_notification(
														f"User '{user_result.username}': {user_result.error}",
														'error'
												)
										elif user_result.error_type == 'login':
												app_state.add_notification(
														f"User '{user_result.username}': Login failed - check credentials",
														'error'
												)
						
						# Add any warnings
						for warning in result.warnings:
								app_state.add_notification(warning, 'warning')
								
				except ImportError as e:
						logger.error(f"Failed to import scraper module: {e}")
						app_state.add_notification(f"Failed to import scraper module: {e}", 'error')
				except Exception as e:
						logger.error(f"Error in scraper execution: {e}")
						app_state.add_notification(f"Error in scraper execution: {e}", 'error')
						
		except Exception as e:
				logger.error(f"Error running scraper: {e}")
				app_state.add_notification(f"Error running scraper: {e}", 'error')
		finally:
				app_state.set_download_status(False)
				logger.info("Scraper process finished")

def parse_file_info(filename: str) -> Dict[str, str]:
		"""Parse user and report information from filename.
		
		Args:
				filename: The filename to parse (format: username_originalfilename.xlsx)
				
		Returns:
				Dictionary with user, report_name, and original filename
		"""
		try:
				name_without_ext = filename.rsplit('.', 1)[0]
				parts = name_without_ext.split('_', 1)
				
				if len(parts) == 2:
						username, report_name = parts
						
						# Check if this is a legacy file (starts with known report type)
						legacy_prefixes = ['Student Usage', 'Skill', 'Assignment', 'Assessment', 'Level Up Progress']
						if any(name_without_ext.startswith(prefix) for prefix in legacy_prefixes):
								return {'user': 'Unknown', 'report_name': name_without_ext, 'filename': filename}
						
						return {'user': username, 'report_name': report_name, 'filename': filename}
				
				# Single part or no underscore - treat as legacy
				return {'user': 'Unknown', 'report_name': name_without_ext, 'filename': filename}
				
		except Exception as e:
				logger.warning(f"Error parsing filename {filename}: {e}")
				return {'user': 'Unknown', 'report_name': filename.rsplit('.', 1)[0], 'filename': filename}

@app.route('/', methods=['GET'])
def index():
		"""Main page displaying reports and configuration."""
		try:
				if getattr(sys, 'frozen', False):  # If running as a frozen executable
						base_path = sys._MEIPASS
				else:
						base_path = os.path.abspath('.')  
				REPORTS_DIR_TMP = os.path.join(base_path, 'reports')  # Adjust based on how reports are bundled
				raw_files = get_report_files(REPORTS_DIR_TMP)
				
				# Filter out combined reports from the main file list
				raw_files = [f for f in raw_files if not f.startswith('Combined')]
				
				# Parse file information for better display
				files_with_info = [parse_file_info(f) for f in raw_files]
				
				# Group files by user for better organization
				files_by_user = {}
				for file_info in files_with_info:
						user = file_info['user']
						if user not in files_by_user:
								files_by_user[user] = []
						files_by_user[user].append(file_info)
				
				# Check for combined all reports file
				combined_report_info = None
				try:
						combined_files = sorted(
								[f for f in os.listdir(REPORTS_DIR_TMP) if f.startswith('Combined_All_Reports_')],
								reverse=True
						)
						if combined_files:
								latest_combined = combined_files[0]
								file_path = os.path.join(REPORTS_DIR_TMP, latest_combined)
								if os.path.exists(file_path):
										file_stats = os.stat(file_path)
										combined_report_info = {
												'filename': latest_combined,
												'size': file_stats.st_size,
												'modified': datetime.fromtimestamp(file_stats.st_mtime)
										}
				except Exception as e:
						logger.debug(f"Error checking for combined report: {e}")
				
				config = load_config()
				selected_date_filter = config.get('date_filter', DATE_FILTERS[0])
				selected_products_filter = config.get('products_filter', PRODUCTS_FILTERS[0])
				selected_tabs = config.get('tabs', {tab["name"]: tab["default"] for tab in TABS})
				users = load_users()
				
				return render_template(
						'scrapper.html',
						files=raw_files,  # Keep for backward compatibility
						files_with_info=files_with_info,
						files_by_user=files_by_user,
						combined_report=combined_report_info,
						download_in_progress=app_state.get_download_status(),
						date_filters=DATE_FILTERS,
						selected_date_filter=selected_date_filter,
						products_filters=PRODUCTS_FILTERS,
						selected_products_filter=selected_products_filter,
						tabs=TABS,
						selected_tabs=selected_tabs,
						users=users
				)
		except Exception as e:
				logger.error(f"Error in index route: {e}")
				return jsonify({'error': 'Internal server error'}), 500

@app.route('/set-filter', methods=['POST'])
def set_filter():
		"""Update filter configuration from form data."""
		try:
				config = load_config()
				
				# Update date filter
				date_filter = request.form.get('date_filter', DATE_FILTERS[0])
				if date_filter not in DATE_FILTERS:
						logger.warning(f"Invalid date filter received: {date_filter}")
						date_filter = DATE_FILTERS[0]
				config['date_filter'] = date_filter
				
				# Update products filter
				products_filter = request.form.get('products_filter', PRODUCTS_FILTERS[0])
				if products_filter not in PRODUCTS_FILTERS:
						logger.warning(f"Invalid products filter received: {products_filter}")
						products_filter = PRODUCTS_FILTERS[0]
				config['products_filter'] = products_filter
				
				# Update tabs selection
				selected_tabs = request.form.getlist('tabs')
				tabs_config = {tab["name"]: (tab["name"] in selected_tabs) for tab in TABS}
				config['tabs'] = tabs_config
				
				save_config(config)
				logger.info(f"Filter configuration updated: date={date_filter}, products={products_filter}, tabs: {selected_tabs}")
				return redirect(url_for('index'))
				
		except Exception as e:
				logger.error(f"Error updating filter configuration: {e}")
				return jsonify({'error': 'Failed to update configuration'}), 500

@app.route('/download/<filename>')
def download(filename: str):
		"""Download a specific report file.
		
		Args:
				filename: Name of the file to download
		"""
		if getattr(sys, 'frozen', False):  # If running as a frozen executable
				base_path = sys._MEIPASS
		else:
				base_path = os.path.abspath('.')
		REPORTS_DIR_TMP = os.path.join(base_path, 'reports')  # Adjust based on how reports are bundled

		try:
				# Security check: ensure filename doesn't contain path traversal
				if not validate_filename(filename):
						logger.warning(f"Potentially malicious filename requested: {filename}")
						return jsonify({'error': 'Invalid filename'}), 400

				file_path = os.path.join(REPORTS_DIR_TMP, filename)
				if not os.path.exists(file_path):
						logger.warning(f"Requested file not found: {filename}")
						return jsonify({'error': 'File not found'}), 404

				logger.info(f"Downloading file: {filename}")
				return send_from_directory(REPORTS_DIR_TMP, filename, as_attachment=True)

		except Exception as e:
				logger.error(f"Error downloading file {filename}: {e}")
				return jsonify({'error': 'Download failed'}), 500

@app.route('/download-combined-reports')
def download_combined_reports():
		"""Download the most recent combined all reports file."""
		try:
				if getattr(sys, 'frozen', False):  # If running as a frozen executable
						base_path = sys._MEIPASS
				else:
						base_path = os.path.abspath('.')
				REPORTS_DIR_TMP = os.path.join(base_path, 'reports')
				
				# Find the most recent combined all reports file
				combined_files = sorted(
						[f for f in os.listdir(REPORTS_DIR_TMP) if f.startswith('Combined_All_Reports_')],
						reverse=True
				)
				
				if not combined_files:
						logger.info("No combined all reports file available")
						return jsonify({'error': 'No combined all reports file available'}), 404
				
				# Get the most recent file
				latest_combined = combined_files[0]
				
				# Security check: ensure filename doesn't contain path traversal
				if not validate_filename(latest_combined):
						logger.warning(f"Potentially malicious filename: {latest_combined}")
						return jsonify({'error': 'Invalid filename'}), 400
				
				file_path = os.path.join(REPORTS_DIR_TMP, latest_combined)
				if not os.path.exists(file_path):
						logger.warning(f"Combined file not found: {latest_combined}")
						return jsonify({'error': 'File not found'}), 404
				
				logger.info(f"Downloading combined all reports file: {latest_combined}")
				return send_from_directory(REPORTS_DIR_TMP, latest_combined, as_attachment=True)
				
		except Exception as e:
				logger.error(f"Error downloading combined all reports file: {e}")
				return jsonify({'error': 'Download failed'}), 500

@app.route('/get-combined-reports-status')
def get_combined_reports_status():
		"""Check if a combined all reports file exists."""
		try:
				if getattr(sys, 'frozen', False):
						base_path = sys._MEIPASS
				else:
						base_path = os.path.abspath('.')
				REPORTS_DIR_TMP = os.path.join(base_path, 'reports')

				# Find combined all reports files
				combined_files = sorted(
						[f for f in os.listdir(REPORTS_DIR_TMP) if f.startswith('Combined_All_Reports_')],
						reverse=True
				)

				if combined_files:
						latest_file = combined_files[0]
						file_path = os.path.join(REPORTS_DIR_TMP, latest_file)
						file_stats = os.stat(file_path)

						return jsonify({
								'exists': True,
								'filename': latest_file,
								'size': file_stats.st_size,
								'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
						})
				else:
						return jsonify({'exists': False})

		except Exception as e:
				logger.error(f"Error checking combined reports status: {e}")
				return jsonify({'exists': False, 'error': str(e)})

@app.route('/scrape', methods=['POST'])
def scrape():
		"""Start the scraping process."""
		try:
				if not app_state.get_download_status():
						logger.info("Starting new scrape job")
						threading.Thread(target=run_scraper, daemon=True).start()
						return jsonify({'status': 'started'})
				else:
						logger.info("Scrape request received but job already running")
						return jsonify({'status': 'already_running'})
		except Exception as e:
				logger.error(f"Error starting scrape job: {e}")
				return jsonify({'error': 'Failed to start scraper'}), 500

@app.route('/scrape-status')
def scrape_status():
		"""Get current scraping status."""
		try:
				return jsonify({'in_progress': app_state.get_download_status()})
		except Exception as e:
				logger.error(f"Error getting scrape status: {e}")
				return jsonify({'error': 'Failed to get status'}), 500

@app.route('/scrape-notifications')
def scrape_notifications():
		"""Get current scraper notifications."""
		try:
				notifications = app_state.get_notifications()
				return jsonify({
						'notifications': notifications,
						'in_progress': app_state.get_download_status()
				})
		except Exception as e:
				logger.error(f"Error getting scrape notifications: {e}")
				return jsonify({'notifications': [], 'in_progress': False})

@app.route('/clear-notifications', methods=['POST'])
def clear_notifications():
		"""Clear all notifications."""
		try:
				app_state.clear_notifications()
				return jsonify({'status': 'ok'})
		except Exception as e:
				logger.error(f"Error clearing notifications: {e}")
				return jsonify({'error': 'Failed to clear notifications'}), 500

@app.route('/scrape-logs')
def scrape_logs():
		"""Get recent scraper logs for notifications (legacy endpoint - kept for compatibility)."""
		try:
				# Use the new notification system
				notifications = app_state.get_notifications()
				
				warnings = []
				errors = []
				
				for notif in notifications:
						if notif['type'] == 'warning':
								warnings.append(notif['message'])
						elif notif['type'] == 'error':
								errors.append(notif['message'])
				
				return jsonify({
						'warnings': warnings,
						'errors': errors
				})
				
		except Exception as e:
				logger.error(f"Error getting scrape logs: {e}")
				return jsonify({'warnings': [], 'errors': []})

@app.route('/get-users', methods=['GET'])
def get_users():
		"""Get list of configured users."""
		try:
				users = load_users()
				return jsonify(users)
		except Exception as e:
				logger.error(f"Error getting users: {e}")
				return jsonify({'error': 'Failed to load users'}), 500

@app.route('/save-users', methods=['POST'])
def save_users_route():
		"""Save users configuration via JSON API."""
		try:
				if not request.is_json:
						return jsonify({'error': 'Content-Type must be application/json'}), 400
						
				users = request.json.get('users', [])
				
				# Validate users data
				if not isinstance(users, list):
						return jsonify({'error': 'Users must be a list'}), 400
						
				for user in users:
						if not validate_user_data(user):
								return jsonify({'error': 'Each user must have username and password fields'}), 400
				
				save_users(users)
				logger.info(f"Saved {len(users)} users via API")
				return jsonify({'status': 'ok'})
				
		except Exception as e:
				logger.error(f"Error saving users: {e}")
				return jsonify({'error': 'Failed to save users'}), 500

@app.route('/upload-users', methods=['POST'])
def upload_users():
		"""Upload users configuration from JSON file."""
		try:
				if 'users_file' not in request.files:
						return jsonify({'error': 'No file uploaded'}), 400
				
				file = request.files['users_file']
				if file.filename == '':
						return jsonify({'error': 'No file selected'}), 400
				
				if not file.filename.endswith('.json'):
						return jsonify({'error': 'File must be a JSON file'}), 400
				
				# Read and parse the uploaded JSON
				file_content = file.read().decode('utf-8')
				try:
						import json
						users_data = json.loads(file_content)
				except json.JSONDecodeError:
						return jsonify({'error': 'Invalid JSON file format'}), 400
				
				# Validate the JSON structure
				if not isinstance(users_data, list):
						return jsonify({'error': 'JSON file must contain an array of users'}), 400
				
				for user in users_data:
						if not validate_user_data(user):
								return jsonify({'error': 'Each user must have username and password fields'}), 400
				
				# Save the new users configuration
				save_users(users_data)
				logger.info(f"Successfully uploaded {len(users_data)} users from file")
				return jsonify({'status': 'ok', 'message': f'Successfully uploaded {len(users_data)} users'})
				
		except json.JSONDecodeError as e:
				logger.error(f"Invalid JSON in uploaded file: {e}")
				return jsonify({'error': 'Invalid JSON file format'}), 400
		except UnicodeDecodeError as e:
				logger.error(f"File encoding error: {e}")
				return jsonify({'error': 'File encoding not supported, please use UTF-8'}), 400
		except Exception as e:
				logger.error(f"Error processing uploaded file: {e}")
				return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/report')
def report():
		"""Display the professional report presentation."""
		try:
			data = get_mock_report_data()
			return render_template('report.html', **data)
		except Exception as e:
			logger.error(f"Error rendering report: {e}")
			return jsonify({'error': 'Internal server error'}), 500

@app.route('/templates/images/<filename>')
def serve_template_image(filename):
		"""Serve images from templates/images directory."""
		try:
			return send_from_directory('templates/images', filename)
		except Exception as e:
			logger.error(f"Error serving image {filename}: {e}")
			return jsonify({'error': 'Image not found'}), 404

def cleanup_reports_directory() -> None:
		"""Clean up the reports directory on startup."""
		try:
				# Determine which directories to clean based on execution context
				directories_to_clean = []

				if getattr(sys, 'frozen', False):
						# Running as PyInstaller executable - clean both directories
						base_path = sys._MEIPASS
						external_reports_dir = os.path.join(os.path.dirname(sys.executable), REPORTS_DIR)
						internal_reports_dir = os.path.join(base_path, REPORTS_DIR)
						directories_to_clean = [external_reports_dir, internal_reports_dir]
				else:
						# Running in development - clean only the local reports directory
						directories_to_clean = [REPORTS_DIR]

				total_files_removed = 0

				for reports_dir in directories_to_clean:
						try:
								os.makedirs(reports_dir, exist_ok=True)

								# Delete all files in the reports directory
								files_removed = 0
								for f in os.listdir(reports_dir):
										file_path = os.path.join(reports_dir, f)
										if os.path.isfile(file_path):
												os.remove(file_path)
												files_removed += 1

								if files_removed > 0:
										logger.info(f"Cleaned up {files_removed} files from {reports_dir}")
										total_files_removed += files_removed
								else:
										logger.info(f"Reports directory {reports_dir} is clean")

						except Exception as e:
								logger.warning(f"Error cleaning up reports directory {reports_dir}: {e}")
								# Continue with other directories

				if total_files_removed > 0:
						logger.info(f"Total cleaned up {total_files_removed} files from all reports directories")
				else:
						logger.info("All reports directories are clean")

		except Exception as e:
				logger.error(f"Error in cleanup_reports_directory: {e}")

def open_browser(host: str = 'localhost', port: int = 5000, delay: float = 1.5) -> None:
		"""Open the default web browser to the application URL.
		
		Args:
				host: Host address (use localhost for browser access)
				port: Port number
				delay: Delay in seconds before opening browser
		"""
		def _open_browser():
				time.sleep(delay)  # Wait for server to start
				url = f"http://{host}:{port}"
				try:
						logger.info(f"Opening browser to {url}")
						webbrowser.open(url)
				except Exception as e:
						logger.warning(f"Could not open browser automatically: {e}")
						logger.info(f"Please open your browser manually and go to {url}")
		
		# Run in a separate thread to avoid blocking the server
		browser_thread = threading.Thread(target=_open_browser, daemon=True)
		browser_thread.start()

if __name__ == '__main__':
		# Configuration
		HOST = os.getenv('FLASK_HOST', '0.0.0.0')  # Server binds to all interfaces
		PORT = int(os.getenv('FLASK_PORT', '5000'))
		BROWSER_HOST = 'localhost'  # Browser should connect to localhost
		AUTO_OPEN_BROWSER = os.getenv('AUTO_OPEN_BROWSER', 'true').lower() == 'true'
		
		cleanup_reports_directory()
		open('app.log', 'w').close()
		logger.info("Cleared app.log file")
		logger.info("Starting Flask application")
		logger.info(f"Server will be available at http://{BROWSER_HOST}:{PORT}")
		
		# Start browser opening in background (if enabled)
		if AUTO_OPEN_BROWSER:
				open_browser(host=BROWSER_HOST, port=PORT)
				logger.info("Browser will open automatically in 1.5 seconds...")
		else:
				logger.info("Auto-open browser disabled. Open your browser manually.")
		
		# Start the server
		try:
				serve(app, host=HOST, port=PORT)
		except KeyboardInterrupt:
				logger.info("Application stopped by user")
		except Exception as e:
				logger.error(f"Server error: {e}")
				raise
