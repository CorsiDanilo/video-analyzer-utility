# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Collect data files and resources for key dependencies
datas += collect_data_files('gradio')
datas += collect_data_files('gradio_client')
datas += collect_data_files('safehttpx')
datas += collect_data_files('groovy')
datas += collect_data_files('pystray')
datas.append(('logo.ico', '.'))

# Safely collect everything for crucial packages to prevent runtime issues
packages_to_collect = [
    'win32ctypes' if sys.platform == 'win32' else None,
    'webview',
    'google.genai',
    'dotenv',
    'yaml',
    'PIL',
    'requests',
    'pystray',
]

for pkg in packages_to_collect:
    if pkg:
        try:
            tmp_ret = collect_all(pkg)
            datas += tmp_ret[0]
            binaries += tmp_ret[1]
            hiddenimports += tmp_ret[2]
        except Exception:
            pass

a = Analysis(
    ['app_main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=['./runtime_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VideoAnalyzer',
)
