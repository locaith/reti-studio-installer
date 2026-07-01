# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the RETI Studio THIN CLIENT (cloud-backed).

No ffmpeg / moviepy / numpy / AI SDK — just a local UI that proxies to the hosted
backend. Build from the project root:
    pyinstaller packaging/reti_client.spec --noconfirm

Set RETI_BUILD_CONSOLE=1 for a console debug build.
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT = os.path.abspath(os.path.join(SPECPATH, ".."))
CONSOLE = os.environ.get("RETI_BUILD_CONSOLE", "0") == "1"

icon_path = os.path.join(PROJECT, "packaging", "app.ico")
icon = icon_path if os.path.exists(icon_path) else None

version_path = os.path.join(PROJECT, "packaging", "version_info.txt")
version_file = version_path if os.path.exists(version_path) else None

datas = [
    (os.path.join(PROJECT, "client", "templates"), "templates"),
    (os.path.join(PROJECT, "client", "static"), "static"),
]

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["anyio", "h11", "httpx", "httpcore", "client.server"]
try:
    hiddenimports += collect_submodules("webview")
    datas += collect_data_files("webview")
    hiddenimports += ["clr", "pythonnet"]
except Exception:
    pass

a = Analysis(
    [os.path.join(PROJECT, "client_launcher.py")],
    pathex=[PROJECT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "PIL", "moviepy", "imageio",
        "imageio_ffmpeg", "scipy", "pandas", "google", "sqlmodel", "sqlalchemy",
    ],
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
    strip=False,
    upx=False,
    console=CONSOLE,
    icon=icon,
    version=version_file,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="RETI Studio")
