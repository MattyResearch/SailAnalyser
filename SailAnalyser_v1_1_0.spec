# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('mpl_toolkits')
datas += collect_data_files('numpy')
datas += collect_data_files('tkinter')
datas += collect_data_files('PIL')
datas += collect_data_files('rs800.ico')
datas += collect_data_files('decimal')
datas += collect_data_files('pandas')
datas += collect_data_files('xml')
datas += collect_data_files('matplotlib')
datas += collect_data_files('openmeteo_requests')
datas += collect_data_files('requests_cache')
datas += collect_data_files('datetime')
datas += collect_data_files('retry_requests')


a = Analysis(
    ['SailAnalyser_v1_1_0.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SailAnalyser_v1_1_0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
