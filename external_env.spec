# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Reports Scrapper with External Environment Support

This version creates an executable that relies on externally installed Playwright
via setup.sh/setup.bat scripts.
"""

import os
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(SPEC))
block_cipher = None

# Data files to include
app_dir = Path(current_dir)
templates_dir = app_dir / 'templates'
datas = []

# Include templates
if templates_dir.exists():
    datas.append((str(templates_dir), 'templates'))

# Include the scraper.py file as data (it will be run as external process)
scraper_file = app_dir / 'scraper.py'
if scraper_file.exists():
    datas.append((str(scraper_file), '.'))

# Hidden imports - minimal set since Playwright will be external
hiddenimports = [
    'pandas',
    'openpyxl', 
    'flask',
    'waitress',
    'subprocess',
    'threading',
    'json',
    'zipfile',
    'tempfile',
    'webbrowser',
    'logging',
]

# Exclude Playwright and other heavy dependencies
excludes = [
    'playwright',  # Will be available in external environment
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
    ['app_external_env.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
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
)