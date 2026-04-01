# Reports Scraper

This project scrapes reports from a website, converts them to XLSX, and serves them via a simple Flask web app.

## Features
- Automates login and report download using Playwright
- Admin Reports access with enhanced filtering
- Converts CSV reports to XLSX
- Simple Flask web app to view/download reports

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   PLAYWRIGHT_BROWSERS_PATH=playwright-browsers playwright install chromium
   ```
2. Configure your credentials in `users.json`:
   ```json
   [
     {
       "username": "your_username",
       "password": "your_password"
     }
   ]
   ```

## Usage

### Run the Scraper Manually
```bash
python scraper.py
```

### Start the Web App
```bash
python app.py
```

## Notes
- Reports are saved in the `reports/` directory.
- The web app lists all available XLSX reports for download. 
