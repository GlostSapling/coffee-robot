# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['d:\\aubo\\aubo_win_gui.py'],
    pathex=[],
    binaries=[('d:\\aubo\\serviceinterface2.dll', '.'), ('d:\\aubo\\libgcc_s_seh-1.dll', '.'), ('d:\\aubo\\libstdc++-6.dll', '.'), ('d:\\aubo\\libwinpthread-1.dll', '.')],
    datas=[],
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
    name='aubo_win_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
