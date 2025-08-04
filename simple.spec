# -*- mode: python ; coding: utf-8 -*-
"""
Simple PyInstaller spec file for Reports Scrapper Application

This spec file creates a standalone executable without Playwright auto-discovery
to avoid browser binary inclusion issues.
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

# Data files to include
datas = []

# Include templates
if templates_dir.exists():
    datas.append((str(templates_dir), 'templates'))

# Include static files if they exist
if static_dir and static_dir.exists():
    datas.append((str(static_dir), 'static'))

# Basic hidden imports without Playwright driver
hiddenimports = [
    'pandas',
    'openpyxl',
    'flask',
    'waitress',
    'threading',
    'subprocess',
    'webbrowser',
    'zipfile',
    'tempfile',
    'logging',
    'argparse',
    'python-dotenv',
    'datetime',
    'app',
    'scraper',
    # Playwright modules (but not driver)
    'playwright',
    'playwright.sync_api',
    'pyee',
    'greenlet',
]

# Exclude unnecessary modules
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
    ['launcher.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],  # No custom hooks to avoid auto-discovery
    hooksconfig={
        'playwright': {
            'browsers': [],  # Explicitly disable browser collection
        }
    },
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)