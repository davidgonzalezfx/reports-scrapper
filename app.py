from flask import Flask, render_template_string, send_from_directory, redirect, url_for, request, jsonify
import os
import subprocess
import threading
import json

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

def run_scraper():
    global download_in_progress
    download_in_progress = True
    subprocess.call(['python3', 'scraper.py'])
    download_in_progress = False

@app.route('/', methods=['GET'])
def index():
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.xlsx')]
    files.sort(reverse=True)
    config = load_config()
    selected_filter = config.get('date_filter', DATE_FILTERS[0])
    selected_tabs = config.get('tabs', {tab["name"]: tab["default"] for tab in TABS})
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Available Reports</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body { background: #f8f9fa; }
        .container { margin-top: 40px; }
        .spinner-border { display: none; }
        #scrape-btn[disabled] + .spinner-border { display: inline-block; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1 class="mb-4">Available Reports</h1>
        <form id="filter-form" class="mb-4" method="post" action="/set-filter">
          <div class="row g-2 align-items-center mb-3">
            <div class="col-auto">
              <label for="date_filter" class="col-form-label">Date Filter:</label>
            </div>
            <div class="col-auto">
              <select class="form-select" id="date_filter" name="date_filter">
                {% for option in date_filters %}
                  <option value="{{ option }}" {% if option == selected_filter %}selected{% endif %}>{{ option }}</option>
                {% endfor %}
              </select>
            </div>
          </div>
          
          <div class="row g-2 mb-3">
            <div class="col-12">
              <label class="form-label">Select Tabs to Download:</label>
            </div>
            <div class="col-12">
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="select-all" onchange="toggleAll(this.checked)">
                <label class="form-check-label" for="select-all">Select All</label>
              </div>
            </div>
            {% for tab in tabs %}
            <div class="col-auto">
              <div class="form-check">
                <input class="form-check-input tab-checkbox" type="checkbox" id="tab-{{ loop.index }}" name="tabs" 
                       value="{{ tab.name }}" {% if selected_tabs.get(tab.name, tab.default) %}checked{% endif %}>
                <label class="form-check-label" for="tab-{{ loop.index }}">{{ tab.name }}</label>
              </div>
            </div>
            {% endfor %}
          </div>
          
          <div class="row">
            <div class="col-auto">
              <button type="submit" class="btn btn-secondary">Save Settings</button>
            </div>
          </div>
        </form>
        
        <table class="table table-striped table-hover">
          <thead class="table-dark">
            <tr><th>Report File</th><th>Download</th></tr>
          </thead>
          <tbody>
          {% for file in files %}
            <tr>
              <td>{{ file }}</td>
              <td><a class="btn btn-primary btn-sm" href="/download/{{ file }}">Download</a></td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
        <form id="scrape-form" action="/scrape" method="post">
          <button id="scrape-btn" type="submit" class="btn btn-success" {% if download_in_progress %}disabled{% endif %}>Run Scraper Now</button>
          <div class="spinner-border text-success ms-2" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </form>
      </div>
      
      <script>
        function toggleAll(checked) {
          document.querySelectorAll('.tab-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
          });
        }
        
        const form = document.getElementById('scrape-form');
        const btn = document.getElementById('scrape-btn');
        const spinner = document.querySelector('.spinner-border');
        form.addEventListener('submit', function(e) {
          e.preventDefault();
          btn.disabled = true;
          spinner.style.display = 'inline-block';
          fetch('/scrape', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
              if (data.status === 'started') {
                // Poll for completion
                function poll() {
                  fetch('/scrape-status').then(r => r.json()).then(status => {
                    if (status.in_progress) {
                      setTimeout(poll, 1000);
                    } else {
                      window.location.reload();
                    }
                  });
                }
                poll();
              }
            });
        });
      </script>
    </body>
    </html>
    ''', files=files, download_in_progress=download_in_progress, 
        date_filters=DATE_FILTERS, selected_filter=selected_filter,
        tabs=TABS, selected_tabs=selected_tabs)

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

if __name__ == '__main__':
    os.makedirs(REPORTS_DIR, exist_ok=True)
    # Delete all files in the reports directory
    for f in os.listdir(REPORTS_DIR):
        file_path = os.path.join(REPORTS_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    app.run(debug=False)
