from flask import Flask, render_template, send_from_directory, redirect, url_for, request, jsonify, send_file
import os
import subprocess
import threading
import json
import zipfile
import tempfile
from datetime import datetime
USERS_FILE = 'users.json'

REPORTS_DIR = 'reports'
CONFIG_FILE = 'scraper_config.json'
DATE_FILTERS = ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year"]
TABS = [
    {"name": "Student Usage", "default": True},
    {"name": "Skill", "default": True},
    {"name": "Assignment", "default": True},
    {"name": "Assessment", "default": True},
    {"name": "Level Up Progress", "default": True},
]

app = Flask(__name__)

# Track scraper status
download_in_progress = False

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"date_filter": DATE_FILTERS[0], "tabs": {tab["name"]: tab["default"] for tab in TABS}}

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def run_scraper():
    global download_in_progress
    download_in_progress = True
    users = load_users()
    subprocess.call(['python3', 'scraper.py', '--users', USERS_FILE])
    download_in_progress = False

@app.route('/', methods=['GET'])
def index():
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')]
    files.sort(reverse=True)
    config = load_config()
    selected_filter = config.get('date_filter', DATE_FILTERS[0])
    selected_tabs = config.get('tabs', {tab["name"]: tab["default"] for tab in TABS})
    users = load_users()
    return render_template('scrapper.html', files=files, download_in_progress=download_in_progress, 
        date_filters=DATE_FILTERS, selected_filter=selected_filter,
        tabs=TABS, selected_tabs=selected_tabs, users=users)

@app.route('/set-filter', methods=['POST'])
def set_filter():
    config = load_config()
    
    # Update date filter
    date_filter = request.form.get('date_filter', DATE_FILTERS[0])
    config['date_filter'] = date_filter
    
    # Update tabs selection
    selected_tabs = request.form.getlist('tabs')
    tabs_config = {tab["name"]: (tab["name"] in selected_tabs) for tab in TABS}
    config['tabs'] = tabs_config
    
    save_config(config)
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)

@app.route('/download-all-zip')
def download_all_zip():
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')]
    
    if not files:
        return jsonify({'error': 'No files available for download'}), 404
    
    # Create a temporary zip file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                file_path = os.path.join(REPORTS_DIR, file)
                zipf.write(file_path, file)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'reports_{timestamp}.zip'
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    finally:
        # Clean up temp file after sending
        def cleanup():
            try:
                os.unlink(temp_zip.name)
            except:
                pass
        threading.Thread(target=cleanup).start()

@app.route('/scrape', methods=['POST'])
def scrape():
    global download_in_progress
    if not download_in_progress:
        threading.Thread(target=run_scraper).start()
        return jsonify({'status': 'started'})
    else:
        return jsonify({'status': 'already_running'})

@app.route('/scrape-status')
def scrape_status():
    return jsonify({'in_progress': download_in_progress})

@app.route('/get-users', methods=['GET'])
def get_users():
    users = load_users()
    return jsonify(users)

@app.route('/save-users', methods=['POST'])
def save_users_route():
    users = request.json.get('users', [])
    save_users(users)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    os.makedirs(REPORTS_DIR, exist_ok=True)
    # Delete all files in the reports directory
    for f in os.listdir(REPORTS_DIR):
        file_path = os.path.join(REPORTS_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    app.run(debug=False)
