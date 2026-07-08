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
# CA bundle for httpx/TLS. httpx 0.28 imports certifi lazily, so PyInstaller's
# static analysis no longer auto-collects certifi/cacert.pem -> frozen app ends
# up with an empty trust store ([X509: NO_CERTIFICATE_OR_CRL_FOUND]). Bundle it
# explicitly; client_launcher._ensure_ca_bundle() points SSL_CERT_FILE at it.
datas += collect_data_files("certifi")

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
# collect_submodules walks the FILESYSTEM, so it bundles every anyio/starlette submodule
# even if Defender has zeroed an __init__.py at build time (which silently breaks
# PyInstaller's import-graph analysis -> "No module named 'anyio._core._eventloop'" and the
# frozen app dies on launch). Belt-and-suspenders after v1.6.9 shipped exactly that crash.
hiddenimports += collect_submodules("anyio")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("httpx")
hiddenimports += collect_submodules("httpcore")
hiddenimports += ["h11", "certifi", "sniffio", "idna", "client.server"]
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
