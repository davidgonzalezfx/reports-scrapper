#!/usr/bin/env python3
"""
Build script for Reports Scrapper executable

This script automates the process of creating a standalone executable
using PyInstaller with proper Playwright browser support.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Run a command and handle errors."""
    logger.info(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed")
        logger.error(f"Error: {e.stderr}")
        return False

def install_playwright_browsers():
    """Install Playwright browsers."""
    logger.info("🎭 Installing Playwright browsers...")
    
    # Try different installation methods
    install_commands = [
        "python -m playwright install chromium",
        "playwright install chromium",
    ]
    
    for cmd in install_commands:
        if run_command(cmd, f"Installing browsers with: {cmd}"):
            return True
    
    logger.warning("⚠️ Could not install Playwright browsers automatically")
    logger.info("💡 Please run 'playwright install chromium' manually after building")
    return False

def clean_build_directories():
    """Clean previous build directories."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            logger.info(f"🧹 Cleaning {dir_name} directory...")
            shutil.rmtree(dir_name)
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

def build_executable():
    """Build the executable using PyInstaller."""
    logger.info("🔨 Building executable with PyInstaller...")
    
    # Ensure we have the spec file
    spec_file = "app.spec"
    if not os.path.exists(spec_file):
        logger.error(f"❌ Spec file {spec_file} not found")
        return False
    
    # Build command
    build_cmd = f"pyinstaller {spec_file} --clean --noconfirm"
    
    return run_command(build_cmd, "Building executable")

def verify_executable():
    """Verify the built executable exists and is functional."""
    exe_path = Path("dist") / "ReportsScrapper"
    
    # Add .exe extension on Windows
    if sys.platform == "win32":
        exe_path = exe_path.with_suffix(".exe")
    
    if not exe_path.exists():
        logger.error(f"❌ Executable not found at {exe_path}")
        return False
    
    logger.info(f"✅ Executable created successfully at {exe_path}")
    
    # Get file size
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    logger.info(f"📦 Executable size: {size_mb:.1f} MB")
    
    return True

def main():
    """Main build process."""
    logger.info("🚀 Starting build process for Reports Scrapper...")
    
    # Check if we're in the right directory
    if not os.path.exists("app.py"):
        logger.error("❌ app.py not found. Make sure you're in the project directory.")
        sys.exit(1)
    
    # Step 1: Clean previous builds
    clean_build_directories()
    
    # Step 2: Install Playwright browsers (optional, can be done after build)
    install_playwright_browsers()
    
    # Step 3: Build executable
    if not build_executable():
        logger.error("❌ Build failed")
        sys.exit(1)
    
    # Step 4: Verify executable
    if not verify_executable():
        logger.error("❌ Executable verification failed")
        sys.exit(1)
    
    logger.info("🎉 Build completed successfully!")
    logger.info("💡 You can now run the executable from the 'dist' directory")
    logger.info("⚠️  Make sure to install Playwright browsers if you haven't already:")
    logger.info("   playwright install chromium")

if __name__ == "__main__":
    main()