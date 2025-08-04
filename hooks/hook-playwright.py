from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os

# Collect playwright data files - this helps PyInstaller find necessary files
datas = collect_data_files('playwright')

# Don't exclude browser binaries since we're bundling them manually
hiddenimports = [
    'playwright._impl._api_structures',
    'playwright._impl._api_types', 
    'playwright._impl._browser_type',
    'playwright._impl._playwright',
    'playwright._impl._sync_api',
    'playwright._impl._sync_base',
    'playwright._impl._page',
    'playwright._impl._browser_context',
]
