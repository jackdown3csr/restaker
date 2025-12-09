# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for building restaker.exe

Usage:
    pyinstaller build.spec

Or use the build script:
    python scripts/build_exe.py
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH).parent

a = Analysis(
    [str(project_root / 'gui' / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include config files
        (str(project_root / 'config.yaml'), '.'),
        (str(project_root / 'config.testnet.yaml'), '.'),
    ],
    hiddenimports=[
        'web3',
        'eth_account',
        'pandas',
        'yaml',
        'pystray',
        'PIL',
        'apscheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.interval',
        'win32crypt',
        'colorama',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='GalacticaRestaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
