#!/usr/bin/env python3
"""
Release Build Script for Reports Scrapper

This script creates a complete, distributable package of the Reports Scrapper
executable with all necessary files and documentation.
"""

import os
import sys
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_release_package():
    """Create a complete release package."""
    logger.info("🚀 Creating Reports Scrapper release package...")
    
    # Create release directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    release_dir = Path(f"release_ReportsScrapper_{timestamp}")
    
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    logger.info(f"📁 Created release directory: {release_dir}")
    
    # Copy executable
    executable_src = Path("dist/ReportsScrapper")
    if not executable_src.exists():
        logger.error("❌ Executable not found. Please run the build first.")
        return False
    
    executable_dst = release_dir / "ReportsScrapper"
    shutil.copy2(executable_src, executable_dst)
    logger.info("✅ Copied executable")
    
    # Copy templates
    templates_src = Path("templates")
    if templates_src.exists():
        templates_dst = release_dir / "templates"
        shutil.copytree(templates_src, templates_dst)
        logger.info("✅ Copied templates")
    
    # Copy documentation
    docs_to_copy = [
        ("README_EXECUTABLE.md", "README.md"),
        ("requirements.txt", "requirements.txt")
    ]
    
    for src_name, dst_name in docs_to_copy:
        src_path = Path(src_name)
        if src_path.exists():
            dst_path = release_dir / dst_name
            shutil.copy2(src_path, dst_path)
            logger.info(f"✅ Copied {src_name} -> {dst_name}")
    
    # Create sample configuration files
    create_sample_configs(release_dir)
    
    # Create launcher scripts for different platforms
    create_launcher_scripts(release_dir)
    
    # Create ZIP package
    zip_path = Path(f"{release_dir}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in release_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(release_dir)
                zipf.write(file_path, arcname)
    
    logger.info(f"📦 Created ZIP package: {zip_path}")
    
    # Display package info
    package_size = zip_path.stat().st_size / (1024 * 1024)
    logger.info(f"📊 Package size: {package_size:.1f} MB")
    
    logger.info("🎉 Release package created successfully!")
    logger.info(f"📁 Directory: {release_dir}")
    logger.info(f"📦 ZIP file: {zip_path}")
    
    return True

def create_sample_configs(release_dir):
    """Create sample configuration files."""
    
    # Sample users.json
    sample_users = {
        "users": [
            {
                "username": "your_username_here",
                "password": "your_password_here"
            }
        ],
        "note": "Replace with your actual credentials. Keep this file secure!"
    }
    
    users_file = release_dir / "users_sample.json"
    with open(users_file, 'w') as f:
        import json
        json.dump(sample_users, f, indent=2)
    
    logger.info("✅ Created sample users configuration")
    
    # Create empty directories
    (release_dir / "reports").mkdir()
    logger.info("✅ Created reports directory")

def create_launcher_scripts(release_dir):
    """Create platform-specific launcher scripts."""
    
    # Windows batch file
    windows_launcher = release_dir / "start_scrapper.bat"
    with open(windows_launcher, 'w') as f:
        f.write("""@echo off
echo Starting Reports Scrapper...
echo.
echo If this is your first run, the application will help you install browser components.
echo The web interface will open automatically in your browser.
echo.
pause
ReportsScrapper.exe
pause
""")
    
    # macOS/Linux shell script
    unix_launcher = release_dir / "start_scrapper.sh"
    with open(unix_launcher, 'w') as f:
        f.write("""#!/bin/bash

echo "Starting Reports Scrapper..."
echo ""
echo "If this is your first run, the application will help you install browser components."
echo "The web interface will open automatically in your browser."
echo ""
echo "Press Enter to continue..."
read

./ReportsScrapper

echo ""
echo "Application closed. Press Enter to exit..."
read
""")
    
    # Make shell script executable
    unix_launcher.chmod(0o755)
    
    logger.info("✅ Created launcher scripts")

def main():
    """Main function."""
    logger.info("🏗️  Reports Scrapper Release Builder")
    logger.info("=" * 50)
    
    # Check if we're in the right directory
    if not Path("dist/ReportsScrapper").exists():
        logger.error("❌ Executable not found. Please build the application first:")
        logger.error("   python build.py")
        logger.error("   or")
        logger.error("   pyinstaller minimal.spec --clean --noconfirm")
        return 1
    
    # Create release package
    if create_release_package():
        logger.info("")
        logger.info("🎯 Next steps:")
        logger.info("1. Test the executable in the release directory")
        logger.info("2. Distribute the ZIP file or directory to users")
        logger.info("3. Users should read the README.md for setup instructions")
        logger.info("")
        logger.info("📋 Users will need to:")
        logger.info("   - Configure their credentials in users.json")
        logger.info("   - Run 'playwright install chromium' (if needed)")
        logger.info("   - Run the executable")
        return 0
    else:
        logger.error("❌ Failed to create release package")
        return 1

if __name__ == "__main__":
    sys.exit(main())