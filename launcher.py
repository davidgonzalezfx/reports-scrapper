#!/usr/bin/env python3
"""
Launcher script for Reports Scrapper executable

This script handles initial setup and launches the main application.
It ensures Playwright browsers are installed before starting the app.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_and_install_browsers():
    """Check if Playwright browsers are installed and install if needed."""
    logger.info("🎭 Checking Playwright browser installation...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        # Try to launch Chromium to check if it's available
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                logger.info("✅ Playwright browsers are already installed")
                return True
            except Exception as e:
                logger.warning(f"⚠️  Browser check failed: {e}")
                logger.info("🔧 Installing Playwright browsers...")
                
                # Try to install browsers
                install_commands = [
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    ["playwright", "install", "chromium"]
                ]
                
                for cmd in install_commands:
                    try:
                        result = subprocess.run(
                            cmd, 
                            capture_output=True, 
                            text=True, 
                            timeout=300
                        )
                        
                        if result.returncode == 0:
                            logger.info("✅ Playwright browsers installed successfully")
                            # Verify installation
                            try:
                                browser = p.chromium.launch(headless=True)
                                browser.close()
                                return True
                            except:
                                continue
                        else:
                            logger.warning(f"Installation attempt failed: {result.stderr}")
                            
                    except Exception as install_error:
                        logger.warning(f"Installation command failed: {install_error}")
                        continue
                
                logger.error("❌ Failed to install Playwright browsers automatically")
                logger.info("💡 Please run 'playwright install chromium' manually")
                return False
                
    except ImportError:
        logger.error("❌ Playwright module not found")
        return False

def main():
    """Main launcher function."""
    logger.info("🚀 Starting Reports Scrapper...")
    
    # Check if we're running from executable or source
    if getattr(sys, 'frozen', False):
        # Running from executable
        app_dir = Path(sys.executable).parent
        logger.info(f"📁 Running from executable in: {app_dir}")
    else:
        # Running from source
        app_dir = Path(__file__).parent
        logger.info(f"📁 Running from source in: {app_dir}")
    
    # Change to application directory
    os.chdir(app_dir)
    
    # Check and install browsers if needed
    browsers_ready = check_and_install_browsers()
    
    if not browsers_ready:
        logger.warning("⚠️  Playwright browsers not ready. Web scraping may fail.")
        logger.info("💡 You can continue and install browsers later with: playwright install chromium")
        
        # Ask user if they want to continue
        try:
            response = input("Continue anyway? (y/n): ").lower().strip()
            if response not in ['y', 'yes']:
                logger.info("👋 Exiting...")
                return
        except (EOFError, KeyboardInterrupt):
            logger.info("👋 Exiting...")
            return
    
    # Import and run the main application
    try:
        logger.info("🌐 Starting web application...")
        
        # Import the main app module
        if getattr(sys, 'frozen', False):
            # When frozen, the modules are embedded
            import app
            app.main()
        else:
            # When running from source
            from app import main as app_main
            app_main()
            
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()