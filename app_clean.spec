# -*- mode: python ; coding: utf-8 -*-
"""
Clean PyInstaller spec file for Reports Scrapper Application

This spec file creates a standalone executable without including browser binaries,
which will be installed separately to avoid code-signing issues.
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(SPEC))
sys.path.insert(0, current_dir)

block_cipher = None

# Define paths
app_dir = Path(current_dir)
templates_dir = app_dir / 'templates'
static_dir = app_dir / 'static' if (app_dir / 'static').exists() else None

# Data files to include (NO browser binaries)
datas = []

# Include templates
if templates_dir.exists():
    datas.append((str(templates_dir), 'templates'))

# Include static files if they exist
if static_dir and static_dir.exists():
    datas.append((str(static_dir), 'static'))

# Include only essential Playwright files (NO browsers)
try:
    import playwright
    playwright_path = Path(playwright.__file__).parent
    
    # Only include the Python driver module, not the actual driver executable
    print("INFO: Including Playwright Python modules only. Browsers will be installed separately.")
    
except ImportError:
    print("Warning: Playwright not found.")

# Hidden imports - libraries that PyInstaller might miss
hiddenimports = [
    'playwright',
    'playwright.sync_api',
    'playwright._impl',
    'playwright._impl._api_structures',
    'playwright._impl._api_types',
    'playwright._impl._browser',
    'playwright._impl._browser_context',
    'playwright._impl._browser_type',
    'playwright._impl._connection',
    'playwright._impl._element_handle',
    'playwright._impl._frame',
    'playwright._impl._helper',
    'playwright._impl._network',
    'playwright._impl._page',
    'playwright._impl._sync_base',
    'playwright._impl._transport',
    'playwright._impl._wait_helper',
    'pandas',
    'openpyxl',
    'flask',
    'waitress',
    'json',
    'threading',
    'subprocess',
    'webbrowser',
    'zipfile',
    'tempfile',
    'logging',
    'argparse',
    'dotenv',
    'datetime',
    'app',  # Include our main app module
    'scraper',  # Include our scraper module
]

# Exclude unnecessary modules to reduce executable size
excludes = [
    'tkinter',
    'unittest',
    'test',
    'distutils',
    'setuptools',
    'pip',
    'wheel',
    'matplotlib',
    'IPython',
    'jupyter',
    'notebook',
]

a = Analysis(
    ['launcher.py'],  # Use launcher as entry point
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],  # Don't use custom hooks that might include browsers
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate files to reduce size
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ReportsScrapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression to reduce file size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logging output
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)