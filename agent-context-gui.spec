# -*- mode: python ; coding: utf-8 -*-
#
# Windows GUI build spec.
#
# Why this spec looks the way it does (read before editing):
#
# 1. UCRT is removed from the bundle.
#    PyInstaller collects ucrtbase.dll and the api-ms-win-crt-*.dll forwarders on
#    some build machines. Shipping them inside a onefile bundle makes Windows
#    resolve the C runtime from the temporary _MEIxxxx extraction directory
#    instead of C:\Windows\System32. The bundled copy does not match the UCRT
#    that Qt6Core.dll was linked against, so the app dies immediately with:
#        Unable to locate procedure entry point ucrtv_open
#        in dynamic link library ...\PySide6\Qt6Core.dll
#    Windows 10 and newer already ship the UCRT, so the bundle must not carry it.
#
# 2. ICU must NOT be bundled -- the opposite treatment from UCRT.
#    Qt6Core.dll imports 20 symbols (ucnv_open, ucnv_fromUnicode, ...) from
#    icuuc.dll, and the PySide6 wheel does not ship that DLL. It is tempting to
#    bundle one; do not. Verified failure mode:
#      * Windows ships its own ICU in System32 (icuuc.dll 36 KB forwarding to
#        icu.dll 2.7 MB). Those exports have NO version suffix: "ucnv_open".
#      * The official ICU build exports suffixed names: "ucnv_open_78"
#        (948 suffixed symbols in the ICU 78 build we tried).
#      * Qt6Core is linked against the Microsoft-style unsuffixed names.
#    Bundling the official ICU therefore makes the bundle copy win over System32
#    and QtCore then fails with
#        ImportError: DLL load failed while importing QtCore: 找不到指定的程序
#    (a missing entry point, not a missing file). Verified with a probe build.
#    Consequence: the app requires the OS-provided ICU, i.e. Windows 10 1903+.
#    Supporting older Windows needs a different Qt (PySide2 / Qt 5.15), not a
#    bigger bundle.
#
# 3. UPX is disabled. Compressing Qt DLLs is a recurring source of load
#    failures and saves little.
#
# 4. runtime_hooks stays empty. A hook (or module-level code in gui.py) that
#    prepends the bundle directory to PATH is what triggered the UCRT failure.
#
# Build with:
#   python -m PyInstaller agent-context-gui.spec --noconfirm --clean
# from the repository root.

block_cipher = None

a = Analysis(
    ["packaging/pyinstaller_gui_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("assets/branding.svg", "assets"),
        ("assets/branding.ico", "assets"),
    ],
    hiddenimports=["agent_context", "agent_context.gui", "PySide6"],
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

_icu = sorted({item[0] for item in a.binaries if "icu" in item[0].lower()})
print(f"[spec] ICU in bundle: {_icu or 'none (uses the OS ICU, requires Windows 10 1903+)'}")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# onedir, not onefile. A onefile build unpacks itself into %TEMP% on every launch;
# on a machine whose %TEMP% is damaged (leftover _MEI folders that cannot even be
# opened by their owner) the bootloader fails with "Could not create temporary
# directory!" before any of our code runs. onedir loads the DLLs from its own
# folder instead, so a broken %TEMP% cannot stop the app from starting.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Agent Context Manager v0.8",
    icon="assets/branding.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
    name="Agent Context Manager v0.8",
)
