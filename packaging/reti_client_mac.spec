# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the RETI Studio thin client on macOS (.app bundle).

Built by GitHub Actions on a macOS runner:
    pyinstaller packaging/reti_client_mac.spec --noconfirm --clean
Produces dist/RETI Studio.app
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT = os.path.abspath(os.path.join(SPECPATH, ".."))
_icns = os.path.join(PROJECT, "packaging", "app.icns")
mac_icon = _icns if os.path.exists(_icns) else None

datas = [
    (os.path.join(PROJECT, "client", "templates"), "templates"),
    (os.path.join(PROJECT, "client", "static"), "static"),
]

hiddenimports = collect_submodules("uvicorn") + ["anyio", "h11", "httpx", "httpcore", "client.server"]
try:
    hiddenimports += collect_submodules("webview")
    datas += collect_data_files("webview")
except Exception:
    pass

a = Analysis(
    [os.path.join(PROJECT, "client_launcher.py")],
    pathex=[PROJECT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "numpy", "PIL", "moviepy", "imageio",
              "imageio_ffmpeg", "scipy", "pandas", "google", "sqlmodel", "sqlalchemy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="RETI Studio", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="RETI Studio")

app = BUNDLE(
    coll,
    name="RETI Studio.app",
    icon=mac_icon,
    bundle_identifier="com.locaith.retistudio",
    info_plist={
        "CFBundleName": "RETI Studio",
        "CFBundleDisplayName": "RETI Studio",
        "CFBundleShortVersionString": "1.2.1",
        "CFBundleVersion": "1.2.1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
