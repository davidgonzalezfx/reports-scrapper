#!/usr/bin/env python3
"""
Complete build script for Flask + Playwright executable.
This script automates the entire build process and creates a ready-to-use executable.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False

def copy_browsers():
    """Copy playwright browsers to the dist folder."""
    source_browser_dir = Path("playwright-browser")
    dist_dir = Path("dist/app")
    target_browser_dir = dist_dir / "playwright-browser"
    
    if not source_browser_dir.exists():
        print(f"❌ Source browser directory not found: {source_browser_dir}")
        return False
        
    if not dist_dir.exists():
        print(f"❌ Dist directory not found: {dist_dir}")
        return False
    
    print(f"📁 Copying browsers from {source_browser_dir} to {target_browser_dir}")
    
    try:
        if target_browser_dir.exists():
            shutil.rmtree(target_browser_dir)
        shutil.copytree(source_browser_dir, target_browser_dir)
        
        browser_dirs = [d for d in target_browser_dir.iterdir() if d.is_dir()]
        print(f"✅ Copied {len(browser_dirs)} browser directories")
        return True
        
    except Exception as e:
        print(f"❌ Error copying browsers: {e}")
        return False

def create_launch_script():
    """Create a launch script for easier execution."""
    launch_script = Path("dist/Launch_Reports_Scraper.command")
    
    script_content = '''#!/bin/bash
# Launch script for Reports Scraper
cd "$(dirname "$0")"
./app/app
'''
    
    try:
        with open(launch_script, 'w') as f:
            f.write(script_content)
        
        # Make it executable
        os.chmod(launch_script, 0o755)
        print("✅ Created launch script: Launch_Reports_Scraper.command")
        return True
        
    except Exception as e:
        print(f"❌ Error creating launch script: {e}")
        return False

def main():
    """Main build process."""
    print("🚀 Flask + Playwright Executable Builder")
    print("=" * 50)
    
    # Step 1: Clean previous builds
    print("🧹 Cleaning previous builds...")
    if Path("dist").exists():
        shutil.rmtree("dist")
    if Path("build").exists():
        shutil.rmtree("build")
    print("✅ Cleaned previous builds")
    
    # Step 2: Build with PyInstaller
    if not run_command("pyinstaller app.spec", "Building executable with PyInstaller"):
        sys.exit(1)
    
    # Step 3: Copy Playwright browsers
    if not copy_browsers():
        sys.exit(1)
    
    # Step 4: Create launch script
    if not create_launch_script():
        print("⚠️  Warning: Failed to create launch script, but executable should still work")
    
    # Step 5: Create README for distribution
    readme_content = """# Reports Scraper - Executable Distribution

## Quick Start
1. Double-click `Launch_Reports_Scraper.command` to start the application
2. Or run `./app/app` from the terminal

## What's Included
- `app/` - Main executable and all dependencies
- `Launch_Reports_Scraper.command` - Easy launch script
- `README.txt` - This file

## Requirements
- macOS (this build)
- No Python installation required
- No additional dependencies needed

## First Run
1. The application will open your browser automatically
2. Configure your users and settings
3. Click "Start Scraping" to begin

## Troubleshooting
- If the app doesn't start, try running from terminal: `./app/app`
- Check the console output for any error messages
- Ensure you have proper permissions to execute the files

## Support
Generated with PyInstaller and Playwright browser automation.
"""
    
    try:
        with open("dist/README.txt", 'w') as f:
            f.write(readme_content)
        print("✅ Created distribution README")
    except Exception as e:
        print(f"⚠️  Warning: Failed to create README: {e}")
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 BUILD COMPLETED SUCCESSFULLY!")
    print("\n📁 Distribution files:")
    print("   dist/")
    print("   ├── app/                     # Main executable directory")
    print("   ├── Launch_Reports_Scraper.command  # Easy launcher")
    print("   └── README.txt               # Distribution guide")
    
    print("\n🚀 To distribute:")
    print("   1. Zip the entire 'dist' folder")
    print("   2. Send to users who need the scraper")
    print("   3. Users just need to unzip and double-click the launcher")
    
    print("\n✨ The executable is ready to use!")

if __name__ == "__main__":
    main()