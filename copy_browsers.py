#!/usr/bin/env python3
"""
Script to copy Playwright browsers to the executable bundle.
This avoids the codesigning issues that occur when PyInstaller tries to process them.
"""

import os
import shutil
import sys
from pathlib import Path

def copy_browsers():
    """Copy playwright browsers to the dist folder."""
    
    # Paths
    source_browser_dir = Path("playwright")
    dist_dir = Path("dist/app")
    target_browser_dir = dist_dir / "playwright"
    
    if not source_browser_dir.exists():
        print(f"❌ Source browser directory not found: {source_browser_dir}")
        return False
        
    if not dist_dir.exists():
        print(f"❌ Dist directory not found: {dist_dir}")
        print("   Please run 'pyinstaller app.spec' first")
        return False
    
    print(f"📁 Copying browsers from {source_browser_dir} to {target_browser_dir}")
    
    try:
        # Remove existing browsers if they exist
        if target_browser_dir.exists():
            shutil.rmtree(target_browser_dir)
            
        # Copy the entire browser directory
        shutil.copytree(source_browser_dir, target_browser_dir)
        
        print(f"✅ Successfully copied browsers to executable bundle")
        
        # List what was copied
        browser_dirs = [d for d in target_browser_dir.iterdir() if d.is_dir()]
        print(f"📊 Copied {len(browser_dirs)} browser directories:")
        for browser_dir in browser_dirs:
            print(f"   - {browser_dir.name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error copying browsers: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Playwright Browser Copy Script")
    print("=" * 50)
    
    if copy_browsers():
        print("\n✅ Browser copy completed successfully!")
        print("🎯 Your executable is ready to use!")
    else:
        print("\n❌ Browser copy failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()