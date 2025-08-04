"""
PyInstaller hook for Playwright

This hook ensures that Playwright and its dependencies are properly
included in the PyInstaller bundle.
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files
import os

# Collect all Playwright modules and data
datas, binaries, hiddenimports = collect_all('playwright')

# Additional hidden imports that might be missed
hiddenimports += [
    'playwright._impl._driver',
    'playwright._impl._browser_type',
    'playwright._impl._connection',
    'playwright._impl._page',
    'playwright._impl._browser',
    'playwright._impl._browser_context',
    'playwright._impl._element_handle',
    'playwright._impl._frame',
    'playwright._impl._helper',
    'playwright._impl._network',
    'playwright._impl._sync_base',
    'playwright._impl._transport',
    'playwright._impl._wait_helper',
    'playwright.sync_api',
]

# Collect Playwright driver files
try:
    import playwright
    playwright_path = os.path.dirname(playwright.__file__)
    driver_data = collect_data_files('playwright._impl.driver')
    datas.extend(driver_data)
except ImportError:
    pass