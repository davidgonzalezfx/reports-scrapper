#!/usr/bin/env python3
"""Test script for the combine_all_reports method."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import combine_all_reports

def main():
    """Test the combine_all_reports function with existing reports."""
    
    print("=" * 60)
    print("Testing combine_all_reports method")
    print("=" * 60)
    
    # Set up the reports directory
    reports_dir = Path("reports")
    
    # Check if reports directory exists
    if not reports_dir.exists():
        print(f"❌ Reports directory '{reports_dir}' does not exist!")
        print("Please ensure you have report files in the 'reports' directory.")
        return 1
    
    # List existing report files
    report_files = list(reports_dir.glob("*.xlsx"))
    
    if not report_files:
        print(f"❌ No Excel files found in '{reports_dir}' directory!")
        print("Please ensure you have .xlsx report files to combine.")
        return 1
    
    print(f"📁 Found {len(report_files)} report files in '{reports_dir}':")
    for file in sorted(report_files)[:10]:  # Show first 10 files
        print(f"   - {file.name}")
    if len(report_files) > 10:
        print(f"   ... and {len(report_files) - 10} more files")
    
    print("\n" + "-" * 40)
    print("Starting combination process...")
    print("-" * 40)
    
    # Run the combine_all_reports function
    try:
        start_time = datetime.now()
        result_path = combine_all_reports(reports_dir)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result_path:
            print(f"\n✅ Success! Combined report created:")
            print(f"   📄 {result_path}")
            print(f"   ⏱️  Processing time: {duration:.2f} seconds")
            
            # Get file size
            file_size = Path(result_path).stat().st_size / 1024  # Size in KB
            print(f"   📊 File size: {file_size:.1f} KB")
            
            print("\n" + "=" * 60)
            print("Test completed successfully!")
            print("Open the generated Excel file to see:")
            print("  • Student Usage sheet with styled summary at bottom")
            print("  • Skill sheet with data bars in column D")
            print("  • All sheets with light blue header styling")
            print("=" * 60)
            
            return 0
        else:
            print("\n❌ Failed to create combined report!")
            print("Check the logs for error details.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during combination: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())