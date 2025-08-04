# Reports Scrapper - Standalone Executable

This is a standalone executable version of the Reports Scrapper application that can run on any system without requiring Python installation.

## Quick Start

1. **Download the executable** - `ReportsScrapper` (27MB)
2. **Run the executable** - Double-click or run from terminal
3. **Install Playwright browsers** (first time only) - The app will guide you through this

## Features

✅ **Standalone executable** - No Python installation required  
✅ **Web-based interface** - Opens automatically in your browser  
✅ **Automated scraping** - Uses Playwright for reliable web automation  
✅ **Multi-user support** - Configure multiple accounts  
✅ **Report management** - Download individual files or ZIP all reports  
✅ **Configurable filters** - Choose date ranges and report types  

## First Run Setup

When you run the executable for the first time:

1. The application will start and check for Playwright browsers
2. If browsers aren't installed, it will offer to install them automatically
3. If automatic installation fails, you can install manually:
   ```bash
   # If you have Python/pip installed:
   pip install playwright
   playwright install chromium
   
   # Or download and run the Playwright installer separately
   ```
4. The web interface will open at `http://localhost:5000`

## Usage

### Configure Users
1. Open the web interface
2. Go to the "Users" section
3. Add usernames and passwords for the accounts you want to scrape
4. Save the configuration

### Run Scraping
1. Select your desired date filter (Today, Last 7 Days, etc.)
2. Choose which report types to download
3. Click "Start Scraping"
4. Wait for the process to complete
5. Download individual reports or all as a ZIP file

### File Locations
- **Reports**: Saved in the `reports/` directory next to the executable
- **Configuration**: Stored in `scraper_config.json`
- **Users**: Stored in `users.json`

## System Requirements

- **Operating System**: macOS, Windows, or Linux
- **Memory**: 2GB RAM minimum
- **Disk Space**: 500MB free space (for browsers and reports)
- **Network**: Internet connection required for scraping

## Troubleshooting

### "Playwright browsers not found"
```bash
# Install browsers manually:
playwright install chromium
```

### "Permission denied" on macOS/Linux
```bash
chmod +x ReportsScrapper
```

### "Application cannot be opened" on macOS
1. Right-click the executable
2. Select "Open"
3. Click "Open" in the security dialog

### Port 5000 already in use
- Close other applications using port 5000
- Or modify the port in the application code

## Security Notes

- ✅ All credentials are stored locally on your machine
- ✅ No data is sent to external servers (except the scraping target)
- ✅ The application runs a local web server only accessible from your machine
- ⚠️ Keep your `users.json` file secure as it contains credentials

## Technical Details

- **Framework**: Flask web application
- **Scraping**: Playwright (Chromium browser automation)
- **Data Processing**: Pandas + OpenPyXL for Excel files
- **Packaging**: PyInstaller for standalone executable
- **Size**: ~27MB executable

## Support

If you encounter issues:

1. Check the console output for error messages
2. Ensure Playwright browsers are properly installed
3. Verify your network connection
4. Check that the target website is accessible

## Version Information

- **Python**: 3.13.3
- **Playwright**: 1.53.0
- **Flask**: 3.1.1
- **Pandas**: 2.3.1
- **Build Date**: August 2025