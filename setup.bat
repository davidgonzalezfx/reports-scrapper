@echo off
REM Reports Scrapper Setup Script for Windows
REM This script installs all necessary dependencies including Playwright and browsers
REM Run this BEFORE using the ReportsScrapper executable

setlocal EnableDelayedExpansion

echo ============================================================
echo   Reports Scrapper - Dependency Setup Script (Windows)
echo ============================================================
echo.

REM Get current directory
set SETUP_DIR=%cd%

echo [INFO] Setup directory: %SETUP_DIR%

REM Check if executable exists
if not exist "%SETUP_DIR%\ReportsScrapper.exe" (
    echo [ERROR] ReportsScrapper.exe not found in current directory!
    echo [ERROR] Please make sure you're running this script in the same directory as the executable.
    pause
    exit /b 1
)

REM Check if already set up
if exist "%SETUP_DIR%\playwright_env" (
    echo [WARNING] Setup directory already exists.
    set /p REPLY="Do you want to reinstall? (y/N): "
    if /i not "!REPLY!"=="y" if /i not "!REPLY!"=="yes" (
        echo [INFO] Setup cancelled.
        pause
        exit /b 0
    )
    rmdir /s /q "%SETUP_DIR%\playwright_env"
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found!
        echo [ERROR] Please install Python 3.8+ from https://python.org
        echo [ERROR] Make sure to check "Add Python to PATH" during installation
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

REM Get Python version
for /f "tokens=2" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python found: !PYTHON_VERSION!

REM Check Python version (basic check)
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

if !PYTHON_MAJOR! LSS 3 (
    echo [ERROR] Python 3.8+ is required. Found: Python !PYTHON_VERSION!
    pause
    exit /b 1
)

echo [INFO] Setting up Python environment...

REM Create virtual environment
!PYTHON_CMD! -m venv "%SETUP_DIR%\playwright_env"
if errorlevel 1 (
    echo [ERROR] Failed to create Python virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
call "%SETUP_DIR%\playwright_env\Scripts\activate.bat"

REM Upgrade pip
python -m pip install --upgrade pip

echo [SUCCESS] Python environment created successfully

echo [INFO] Installing Playwright and dependencies...

REM Install required packages
pip install playwright pandas openpyxl python-dotenv
if errorlevel 1 (
    echo [ERROR] Failed to install Python packages
    pause
    exit /b 1
)

echo [INFO] Installing Playwright browsers (this may take a few minutes)...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers
    pause
    exit /b 1
)

echo [SUCCESS] Playwright installation completed

echo [INFO] Verifying installation...

REM Test Playwright
python -c "
import sys
try:
    from playwright.sync_api import sync_playwright
    print('✓ Playwright import successful')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://example.com')
        title = page.title()
        browser.close()
        print(f'✓ Browser test successful: {title}')
    
    print('✓ All tests passed!')
    sys.exit(0)
except Exception as e:
    print(f'✗ Test failed: {e}')
    sys.exit(1)
"

if errorlevel 1 (
    echo [ERROR] Playwright verification failed
    pause
    exit /b 1
)

echo [SUCCESS] All dependencies verified successfully!

echo [INFO] Creating run script...

REM Create Windows run script
(
echo @echo off
echo echo Starting Reports Scrapper...
echo echo.
echo.
echo REM Get the directory where this script is located
echo set SCRIPT_DIR=%%~dp0
echo.
echo REM Check if virtual environment exists
echo if not exist "%%SCRIPT_DIR%%playwright_env" ^(
echo     echo ERROR: Python environment not found!
echo     echo Please run setup.bat first to install dependencies.
echo     pause
echo     exit /b 1
echo ^)
echo.
echo REM Activate virtual environment
echo call "%%SCRIPT_DIR%%playwright_env\Scripts\activate.bat"
echo.
echo REM Set environment variables
echo set PYTHONPATH=%%SCRIPT_DIR%%playwright_env\Lib\site-packages;%%PYTHONPATH%%
echo.
echo echo Environment activated. Starting application...
echo echo The web interface will open at http://localhost:5000
echo echo Press Ctrl+C to stop the application
echo echo.
echo.
echo REM Run the executable
echo "%%SCRIPT_DIR%%ReportsScrapper.exe"
echo.
echo echo.
echo echo Application stopped.
echo pause
) > "%SETUP_DIR%\run_scrapper.bat"

echo [SUCCESS] Run script created: run_scrapper.bat

echo.
echo ============================================================
echo [SUCCESS] Setup completed successfully!
echo.
echo Next steps:
echo 1. Configure your credentials in users.json
echo 2. Run the application using: run_scrapper.bat
echo.
echo The application will start a web server at http://localhost:5000
echo Your browser should open automatically when you run it.
echo ============================================================
echo.

pause