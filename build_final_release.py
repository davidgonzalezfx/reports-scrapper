#!/usr/bin/env python3
"""
Final Release Builder for Reports Scrapper with External Environment Setup

This creates a complete package with setup scripts and executable.
"""

import os
import sys
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_final_release():
    """Create the final release package."""
    logger.info("🚀 Creating Reports Scrapper FINAL release package...")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    release_dir = Path(f"ReportsScrapper_v2_{timestamp}")
    
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    logger.info(f"📁 Created release directory: {release_dir}")
    
    # Copy executable
    executable_src = Path("dist/ReportsScrapper")
    if not executable_src.exists():
        logger.error("❌ Executable not found. Please build first.")
        return False
    
    shutil.copy2(executable_src, release_dir / "ReportsScrapper")
    logger.info("✅ Copied executable")
    
    # Copy scraper.py (needed for external process)
    scraper_src = Path("scraper.py")
    if scraper_src.exists():
        shutil.copy2(scraper_src, release_dir / "scraper.py")
        logger.info("✅ Copied scraper.py")
    
    # Copy templates
    templates_src = Path("templates")
    if templates_src.exists():
        shutil.copytree(templates_src, release_dir / "templates")
        logger.info("✅ Copied templates")
    
    # Copy setup scripts
    setup_files = [
        ("setup.sh", "setup.sh"),
        ("setup.bat", "setup.bat"),
    ]
    
    for src_name, dst_name in setup_files:
        src_path = Path(src_name)
        if src_path.exists():
            dst_path = release_dir / dst_name
            shutil.copy2(src_path, dst_path)
            # Make shell script executable
            if dst_name.endswith('.sh'):
                dst_path.chmod(0o755)
            logger.info(f"✅ Copied {src_name}")
    
    # Create sample files
    create_sample_files(release_dir)
    
    # Create documentation
    create_documentation(release_dir)
    
    # Create directories
    (release_dir / "reports").mkdir()
    logger.info("✅ Created reports directory")
    
    # Create ZIP package
    zip_path = Path(f"{release_dir}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in release_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(release_dir)
                zipf.write(file_path, arcname)
    
    package_size = zip_path.stat().st_size / (1024 * 1024)
    logger.info(f"📦 Created ZIP package: {zip_path} ({package_size:.1f} MB)")
    
    return True, release_dir, zip_path

def create_sample_files(release_dir):
    """Create sample configuration files."""
    
    # Sample users.json
    sample_users = [
        {
            "username": "your_username_here",
            "password": "your_password_here",
            "note": "Replace with actual credentials"
        }
    ]
    
    users_file = release_dir / "users_sample.json"
    with open(users_file, 'w') as f:
        import json
        json.dump(sample_users, f, indent=2)
    
    logger.info("✅ Created sample users configuration")

def create_documentation(release_dir):
    """Create comprehensive documentation."""
    
    readme_content = """# Reports Scrapper v2.0 - Complete Package

🎉 **NEW APPROACH**: This version uses external Python environment setup for maximum reliability!

## Quick Start (3 Steps)

### Step 1: Run Setup Script
**IMPORTANT**: Run this BEFORE using the executable!

**Mac/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

This will:
- Install Python (if needed)
- Create isolated Python environment 
- Install Playwright and browsers
- Verify everything works

### Step 2: Configure Users
Copy `users_sample.json` to `users.json` and add your credentials:
```json
[
  {
    "username": "your_actual_username",
    "password": "your_actual_password"
  }
]
```

### Step 3: Run Application
**Mac/Linux:**
```bash
./run_scrapper.sh
```

**Windows:**
```cmd
run_scrapper.bat
```

## What's New in v2.0

✅ **Reliable Playwright Setup** - No more browser installation issues  
✅ **Cross-Platform Scripts** - Works on Mac, Linux, and Windows  
✅ **Isolated Environment** - Doesn't interfere with system Python  
✅ **Better Error Handling** - Clear messages when something goes wrong  
✅ **Automatic Testing** - Setup verifies everything works before you start  

## File Structure

```
ReportsScrapper_v2/
├── ReportsScrapper           # Main executable
├── scraper.py               # Scraper logic (runs in Python env)
├── setup.sh                 # Setup script (Mac/Linux)
├── setup.bat                # Setup script (Windows)
├── run_scrapper.sh          # Run script (Mac/Linux) 
├── run_scrapper.bat         # Run script (Windows)
├── users_sample.json        # Sample user configuration
├── templates/               # Web interface templates
├── reports/                 # Downloaded reports go here
└── README.md               # This file
```

## How It Works

1. **Setup Phase**: Creates `playwright_env/` directory with Python + Playwright
2. **Runtime**: Executable finds the Python environment and runs scraper externally
3. **Web Interface**: Runs on http://localhost:5000 with real-time status

## Troubleshooting

### "Setup failed" errors
- Ensure you have internet connection
- On Linux, you may need `sudo` for system packages
- On Mac, install Homebrew first if requested

### "Playwright not available" errors  
- Re-run the setup script: `./setup.sh` or `setup.bat`
- Check that `playwright_env/` directory exists

### "Permission denied" on Mac/Linux
```bash
chmod +x setup.sh
chmod +x run_scrapper.sh
```

### Web interface won't open
- Check if port 5000 is available
- Manually visit http://localhost:5000
- Check console output for errors

## System Requirements

- **OS**: macOS 10.14+, Windows 10+, or modern Linux
- **Memory**: 2GB RAM minimum
- **Disk**: 1GB free space (for Python environment + browsers)
- **Network**: Internet connection for setup and scraping

## Security Notes

- All credentials stored locally in `users.json`
- No data sent to external servers (except scraping target)
- Python environment is isolated in `playwright_env/`
- Keep `users.json` secure and don't share it

## Support

1. Check console output for detailed error messages
2. Verify setup completed successfully (`playwright_env/` should exist)
3. Test system status via web interface
4. Re-run setup if needed

---

**Version**: 2.0  
**Build Date**: August 2025  
**Python**: 3.8+ Required  
**Playwright**: Auto-installed by setup scripts
"""

    readme_file = release_dir / "README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    logger.info("✅ Created documentation")

def main():
    """Main function."""
    logger.info("🏗️  Reports Scrapper FINAL Release Builder")
    logger.info("=" * 60)
    
    if not Path("dist/ReportsScrapper").exists():
        logger.error("❌ Executable not found. Please build first:")
        logger.error("   pyinstaller external_env.spec --clean --noconfirm")
        return 1
    
    success, release_dir, zip_path = create_final_release()
    
    if success:
        logger.info("")
        logger.info("🎉 FINAL RELEASE CREATED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"📁 Release Directory: {release_dir}")
        logger.info(f"📦 ZIP Package: {zip_path}")
        logger.info("")
        logger.info("📋 DISTRIBUTION INSTRUCTIONS:")
        logger.info("1. Send users the ZIP file")
        logger.info("2. Users should extract and read README.md")
        logger.info("3. Users must run setup script FIRST")
        logger.info("4. Then they can run the application")
        logger.info("")
        logger.info("✨ This version should work reliably on all platforms!")
        return 0
    else:
        logger.error("❌ Failed to create release")
        return 1

if __name__ == "__main__":
    sys.exit(main())