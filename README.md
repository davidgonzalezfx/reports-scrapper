# Reports Scraper

This project scrapes reports from a website, converts them to XLSX, and serves them via a simple Flask web app.

## Features
- Automates login and report download using Playwright
- Converts CSV reports to XLSX
- Simple Flask web app to view/download reports
- Manual and scheduled scraping (weekly)

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
2. Configure your credentials in `scraper.py` (to be added).

## Usage

### Run the Scraper Manually
```bash
python scraper.py
```

### Start the Web App
```bash
python app.py
```

### Schedule Weekly Scraping
The scheduler is integrated; just run:
```bash
python scheduler.py
```

## Notes
- Reports are saved in the `reports/` directory.
- The web app lists all available XLSX reports for download. 
