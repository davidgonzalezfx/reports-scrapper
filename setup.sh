#!/bin/bash

# Reports Scrapper Setup Script
# This script installs all necessary dependencies including Playwright and browsers
# Run this BEFORE using the ReportsScrapper executable

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "  Reports Scrapper - Dependency Setup Script"
    echo "============================================================"
    echo -e "${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install Python on different systems
install_python() {
    local os_type=$1
    
    print_status "Installing Python..."
    
    case $os_type in
        "macos")
            if command_exists brew; then
                brew install python3
            else
                print_error "Homebrew not found. Please install Homebrew first:"
                print_error "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                return 1
            fi
            ;;
        "linux")
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            elif command_exists yum; then
                sudo yum install -y python3 python3-pip
            elif command_exists dnf; then
                sudo dnf install -y python3 python3-pip
            elif command_exists zypper; then
                sudo zypper install -y python3 python3-pip
            else
                print_error "Package manager not found. Please install Python 3.8+ manually."
                return 1
            fi
            ;;
        *)
            print_error "Unsupported OS for automatic Python installation."
            print_error "Please install Python 3.8+ manually from https://python.org"
            return 1
            ;;
    esac
}

# Function to install Node.js (needed for Playwright browsers)
install_nodejs() {
    local os_type=$1
    
    print_status "Installing Node.js (required for Playwright)..."
    
    case $os_type in
        "macos")
            if command_exists brew; then
                brew install node
            else
                print_warning "Homebrew not found. Skipping Node.js installation."
                print_warning "You may need to install Node.js manually if Playwright installation fails."
            fi
            ;;
        "linux")
            # Install Node.js using NodeSource repository
            if command_exists curl; then
                curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                if command_exists apt-get; then
                    sudo apt-get install -y nodejs
                elif command_exists yum; then
                    sudo yum install -y nodejs npm
                elif command_exists dnf; then
                    sudo dnf install -y nodejs npm
                fi
            else
                print_warning "curl not found. Skipping Node.js installation."
            fi
            ;;
        *)
            print_warning "Skipping Node.js installation for this OS."
            ;;
    esac
}

# Function to create and setup Python virtual environment
setup_python_env() {
    local setup_dir="$1"
    
    print_status "Setting up Python environment..."
    
    # Create virtual environment
    if ! python3 -m venv "$setup_dir/playwright_env"; then
        print_error "Failed to create Python virtual environment"
        return 1
    fi
    
    # Activate virtual environment
    source "$setup_dir/playwright_env/bin/activate"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    print_success "Python environment created successfully"
}

# Function to install Playwright and dependencies
install_playwright() {
    local setup_dir="$1"
    
    print_status "Installing Playwright and dependencies..."
    
    # Activate virtual environment
    source "$setup_dir/playwright_env/bin/activate"
    
    # Install required packages
    pip install playwright pandas openpyxl python-dotenv
    
    # Install Playwright browsers
    print_status "Installing Playwright browsers (this may take a few minutes)..."
    playwright install chromium
    
    # Install system dependencies for browsers
    print_status "Installing system dependencies for browsers..."
    playwright install-deps chromium || print_warning "Could not install system dependencies automatically"
    
    print_success "Playwright installation completed"
}

# Function to verify installation
verify_installation() {
    local setup_dir="$1"
    
    print_status "Verifying installation..."
    
    # Activate virtual environment
    source "$setup_dir/playwright_env/bin/activate"
    
    # Test Playwright
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
" || {
        print_error "Playwright verification failed"
        return 1
    }
    
    print_success "All dependencies verified successfully!"
}

# Function to create run script
create_run_script() {
    local setup_dir="$1"
    
    print_status "Creating run script..."
    
    cat > "$setup_dir/run_scrapper.sh" << 'EOF'
#!/bin/bash

# Reports Scrapper Runner Script
# This script activates the Python environment and runs the executable

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Starting Reports Scrapper..."

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/playwright_env" ]; then
    print_error "Python environment not found!"
    print_error "Please run setup.sh first to install dependencies."
    exit 1
fi

# Activate virtual environment
source "$SCRIPT_DIR/playwright_env/bin/activate"

# Export Python path so the executable can find Playwright
export PYTHONPATH="$SCRIPT_DIR/playwright_env/lib/python*/site-packages:$PYTHONPATH"

# Set Playwright browsers path
export PLAYWRIGHT_BROWSERS_PATH="$SCRIPT_DIR/playwright_env/lib/python*/site-packages/playwright/driver/package/.local-browsers"

print_status "Environment activated. Starting application..."
print_status "The web interface will open at http://localhost:5000"
print_status "Press Ctrl+C to stop the application"
echo ""

# Run the executable
"$SCRIPT_DIR/ReportsScrapper"

print_success "Application stopped."
EOF

    chmod +x "$setup_dir/run_scrapper.sh"
    print_success "Run script created: run_scrapper.sh"
}

# Function to create Windows batch file
create_windows_runner() {
    local setup_dir="$1"
    
    cat > "$setup_dir/run_scrapper.bat" << 'EOF'
@echo off
echo Starting Reports Scrapper...
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%playwright_env" (
    echo ERROR: Python environment not found!
    echo Please run setup.sh first to install dependencies.
    pause
    exit /b 1
)

REM Activate virtual environment
call "%SCRIPT_DIR%playwright_env\Scripts\activate.bat"

REM Set environment variables
set PYTHONPATH=%SCRIPT_DIR%playwright_env\Lib\site-packages;%PYTHONPATH%

echo Environment activated. Starting application...
echo The web interface will open at http://localhost:5000
echo Press Ctrl+C to stop the application
echo.

REM Run the executable
"%SCRIPT_DIR%ReportsScrapper.exe"

echo.
echo Application stopped.
pause
EOF

    print_success "Windows run script created: run_scrapper.bat"
}

# Main setup function
main() {
    print_header
    
    # Get current directory (where the executable should be)
    SETUP_DIR="$(pwd)"
    
    print_status "Setup directory: $SETUP_DIR"
    
    # Detect operating system
    OS_TYPE=$(detect_os)
    print_status "Detected OS: $OS_TYPE"
    
    # Check if executable exists
    if [ ! -f "$SETUP_DIR/ReportsScrapper" ] && [ ! -f "$SETUP_DIR/ReportsScrapper.exe" ]; then
        print_error "ReportsScrapper executable not found in current directory!"
        print_error "Please make sure you're running this script in the same directory as the executable."
        exit 1
    fi
    
    # Check if already set up
    if [ -d "$SETUP_DIR/playwright_env" ]; then
        print_warning "Setup directory already exists."
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled."
            exit 0
        fi
        rm -rf "$SETUP_DIR/playwright_env"
    fi
    
    # Check for Python
    if ! command_exists python3; then
        print_warning "Python 3 not found. Attempting to install..."
        if ! install_python "$OS_TYPE"; then
            print_error "Failed to install Python. Please install Python 3.8+ manually."
            exit 1
        fi
    else
        print_success "Python 3 found: $(python3 --version)"
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8+ is required. Found: Python $PYTHON_VERSION"
        exit 1
    fi
    
    # Install Node.js if needed (helps with some Playwright installations)
    if ! command_exists node; then
        print_status "Node.js not found. Installing..."
        install_nodejs "$OS_TYPE"
    fi
    
    # Setup Python environment
    if ! setup_python_env "$SETUP_DIR"; then
        print_error "Failed to setup Python environment"
        exit 1
    fi
    
    # Install Playwright
    if ! install_playwright "$SETUP_DIR"; then
        print_error "Failed to install Playwright"
        exit 1
    fi
    
    # Verify installation
    if ! verify_installation "$SETUP_DIR"; then
        print_error "Installation verification failed"
        exit 1
    fi
    
    # Create run scripts
    create_run_script "$SETUP_DIR"
    
    if [ "$OS_TYPE" = "windows" ] || command_exists cmd; then
        create_windows_runner "$SETUP_DIR"
    fi
    
    print_header
    print_success "Setup completed successfully!"
    echo ""
    print_status "Next steps:"
    print_status "1. Configure your credentials in users.json"
    print_status "2. Run the application using:"
    print_status "   ./run_scrapper.sh  (Mac/Linux)"
    print_status "   run_scrapper.bat   (Windows)"
    echo ""
    print_status "The application will start a web server at http://localhost:5000"
    print_status "Your browser should open automatically when you run it."
    echo ""
}

# Run main function
main "$@"