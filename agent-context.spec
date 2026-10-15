# -*- mode: python ; coding: utf-8 -*-
#
# Windows CLI build spec.
#
# This spec was previously incompatible with PyInstaller 6: Analysis() was
# called with cipher=, win_no_prefer_redirects= and win_private_assemblies=,
# all of which were removed in PyInstaller 6. The build failed and
# dist\agent-context.exe was never produced. The arguments are gone now.
#
# UCRT is stripped for the same reason as in agent-context-gui.spec: bundling
# it breaks DLL resolution at startup.

block_cipher = None

a = Analysis(
    ["packaging/pyinstaller_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=["agent_context", "typer", "rich"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

_ucrt = [
    item for item in a.binaries
    if item[0].lower() == "ucrtbase.dll"
    or item[0].lower().startswith("api-ms-win-crt-")
]
if _ucrt:
    a.binaries = [item for item in a.binaries if item not in _ucrt]
    print(f"[spec] removed {len(_ucrt)} UCRT binaries from the bundle")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# onedir, not onefile. A onefile build unpacks itself into %TEMP% at every start;
# on machines where %TEMP% is damaged (leftover _MEI folders that cannot be opened)
# the bootloader dies with "Could not create temporary directory!". An onedir build
# loads its DLLs straight from its own folder and never needs a writable %TEMP%.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="agent-context",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="agent-context",
)
