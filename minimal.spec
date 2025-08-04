# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(SPEC))
block_cipher = None

# Data files
app_dir = Path(current_dir)
templates_dir = app_dir / 'templates'

datas = []
if templates_dir.exists():
    datas.append((str(templates_dir), 'templates'))

hiddenimports = [
    'pandas',
    'openpyxl', 
    'flask',
    'waitress',
    'scraper',
]

excludes = [
    'playwright',  # Exclude at build time - will be imported dynamically
    'tkinter',
    'unittest',
    'test',
]

a = Analysis(
    ['no_playwright.py'],
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