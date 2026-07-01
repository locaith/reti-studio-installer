# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for RETI Studio (one-folder desktop build).

Build from the project root:
    pyinstaller packaging/reti_studio.spec --noconfirm

Set RETI_BUILD_CONSOLE=1 to build a console variant for debugging.
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

PROJECT = os.path.abspath(os.path.join(SPECPATH, ".."))
CONSOLE = os.environ.get("RETI_BUILD_CONSOLE", "0") == "1"

icon_path = os.path.join(PROJECT, "packaging", "app.ico")
icon = icon_path if os.path.exists(icon_path) else None

datas = [
    (os.path.join(PROJECT, "app", "templates"), "app/templates"),
    (os.path.join(PROJECT, "app", "static"), "app/static"),
    (os.path.join(PROJECT, ".env.example"), "."),
    (os.path.join(PROJECT, "sample_campaign.json"), "."),
    (os.path.join(PROJECT, "vendor", "ffmpeg", "ffmpeg.exe"), "vendor/ffmpeg"),
]
datas += collect_data_files("imageio_ffmpeg")

# Some libraries read their own version via importlib.metadata at import time;
# bundle that dist metadata so the frozen app can find it.
for _pkg in ("imageio", "imageio_ffmpeg", "moviepy", "numpy"):
    try:
        datas += copy_metadata(_pkg)
    except Exception:
        pass

hiddenimports = []
hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "anyio",
    "h11",
    "click",
    "email_validator",
]

# pywebview (desktop window). Guarded so the spec still builds if it is not installed;
# at runtime the launcher falls back to the default browser when webview is unavailable.
try:
    hiddenimports += collect_submodules("webview")
    datas += collect_data_files("webview")
    hiddenimports += ["clr", "pythonnet"]
except Exception:
    pass

a = Analysis(
    [os.path.join(PROJECT, "launcher.py")],
    pathex=[PROJECT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RETI Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="RETI Studio",
)
