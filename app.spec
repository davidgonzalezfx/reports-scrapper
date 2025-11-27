# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Get the current directory
current_dir = os.getcwd()

a = Analysis(
    ['app.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('scraper_config.json', '.'),
        ('playwright-browsers', 'playwright-browsers')
    ],
    hiddenimports=[
        'playwright.sync_api',
        'playwright._impl._api_structures',
        'playwright._impl._api_types',
        'playwright._impl._browser_type',
        'playwright._impl._playwright',
        'playwright._impl._sync_api',
        'playwright._impl._sync_base',
        'playwright._impl._page',
        'playwright._impl._browser_context',
        'pandas',
        'openpyxl',
        'flask',
        'waitress',
        'apscheduler',
        'dotenv',
        'utils'
    ],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],  # Don't exclude playwright browsers, we bundle them manually
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='app',
    debug=True,
    strip=False,
    upx=False,  # Disable UPX compression to avoid issues
    console=True,  # Set to windowed app
    disable_windowed_traceback=False,
    target_arch=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # Disable UPX completely
    upx_exclude=[],
    name='app',
)
