"""Desktop launcher for the RETI Studio thin client.

Starts the small local proxy server (client/server.py) in a background thread and
opens a native desktop window pointing at it. No AI key, no ffmpeg, no rendering —
everything is proxied to the hosted cloud backend.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback


def _log_dir() -> str:
    if sys.platform == "darwin":
        d = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "RETI Studio")
    else:
        d = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "RETI Studio")
    os.makedirs(d, exist_ok=True)
    return d


def _log(msg: str) -> None:
    """Write a diagnostic line straight to client.log — independent of whether
    stdout/stderr got redirected. Frozen windowed builds sometimes leave stdout
    non-None, so print()-based logging silently vanished; this always writes."""
    try:
        with open(os.path.join(_log_dir(), "client.log"), "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def _ensure_ca_bundle() -> None:
    """Point OpenSSL/httpx at a real CA-certificate bundle.

    In the frozen (PyInstaller) build ``certifi.where()`` can resolve to a path
    inside the PYZ archive that has no real file on disk, leaving the SSL trust
    store empty -> ``[X509: NO_CERTIFICATE_OR_CRL_FOUND]`` on every HTTPS call
    (this is what makes activation fail with "Không kết nối được máy chủ"). httpx
    0.28 checks ``SSL_CERT_FILE`` before certifi, so exporting a valid bundled
    path fixes it regardless of freeze quirks or a Windows cert store that isn't
    ready yet right after a reboot.
    """
    cur = os.environ.get("SSL_CERT_FILE")
    if cur and os.path.isfile(cur) and os.path.getsize(cur) > 0:
        return
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(base, "certifi", "cacert.pem"))
        candidates.append(os.path.join(base, "cacert.pem"))
    try:
        import certifi

        candidates.append(certifi.where())
    except Exception:
        pass
    for path in candidates:
        try:
            if path and os.path.isfile(path) and os.path.getsize(path) > 0:
                os.environ["SSL_CERT_FILE"] = path
                os.environ.setdefault("SSL_CERT_DIR", os.path.dirname(path))
                os.environ.setdefault("REQUESTS_CA_BUNDLE", path)
                return
        except Exception:
            continue


# Must run before client.server (and therefore httpx) is imported.
_ensure_ca_bundle()


def _ensure_streams() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        if sys.platform == "darwin":
            d = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "RETI Studio")
        else:
            d = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "RETI Studio")
        os.makedirs(d, exist_ok=True)
        stream = open(os.path.join(d, "client.log"), "a", encoding="utf-8")
    except Exception:
        stream = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _make_server(host: str, port: int):
    import uvicorn

    from client.server import app

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    return server


def _wait_for_http(url: str, timeout: float = 30.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def _is_up(url: str) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _setup_webview_env() -> None:
    """Give WebView2 a dedicated, writable per-user data folder.

    Without this, pywebview lets WebView2 pick a default cache folder that can be
    locked (by a just-closed instance) or shared with other apps, which makes
    ``webview.start()`` throw -> the app falls back to opening in a web BROWSER
    instead of its native window. A fixed per-user folder makes the native window
    reliable across reopen/relaunch.
    """
    try:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        udf = os.path.join(base, "RETI Studio", "WebView2")
        os.makedirs(udf, exist_ok=True)
        os.environ.setdefault("WEBVIEW2_USER_DATA_FOLDER", udf)
    except Exception:
        pass


def _open_app_window(url: str) -> bool:
    """Fallback when pywebview can't create a native window: open Edge/Chrome in
    --app mode (a clean frameless window, no tabs/address bar) so it still looks
    like an app, not a browser tab. Returns True if a browser was launched."""
    import subprocess

    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if exe and os.path.exists(exe):
            try:
                subprocess.Popen([exe, f"--app={url}", "--window-size=1360,900", "--new-window"])
                _log(f"fallback: opened app-mode window via {exe}")
                return True
            except Exception as e:
                _log(f"fallback app-mode failed for {exe}: {e!r}")
    return False


def main() -> int:
    _ensure_streams()
    _log(f"=== launch: frozen={getattr(sys, 'frozen', False)} argv={sys.argv} ===")
    _setup_webview_env()
    _log(f"WEBVIEW2_USER_DATA_FOLDER={os.environ.get('WEBVIEW2_USER_DATA_FOLDER')}")
    host, port = "127.0.0.1", 17650
    url = f"http://{host}:{port}/"

    # Single instance: if one is already serving, don't start a second server —
    # a port clash would kill this instance's server thread and can break its
    # webview (the cause of the "opens in a browser" symptom). Just point the
    # window at the running instance instead.
    if _is_up(url + "health"):
        _log("existing instance detected on 17650 -> not starting a 2nd server")
        ready = True
    else:
        server = _make_server(host, port)
        threading.Thread(target=server.run, daemon=True).start()
        ready = _wait_for_http(url + "health")
    _log(f"server ready={ready}")

    if "--selftest" in sys.argv:
        print(f"CLIENT SELFTEST: {'OK' if ready else 'FAIL'} {url}")
        return 0 if ready else 1

    try:
        import webview

        _log(f"webview imported ver={getattr(webview, '__version__', '?')}; creating window")
        webview.create_window("RETI Studio", url, width=1360, height=900, min_size=(1024, 680))
        try:
            _log("webview.start(gui='edgechromium')")
            webview.start(gui="edgechromium")
            _log("webview closed normally (edgechromium)")
        except Exception as start_exc:
            _log("edgechromium FAILED:\n" + traceback.format_exc())
            webview.create_window("RETI Studio", url, width=1360, height=900, min_size=(1024, 680))
            _log("webview.start() default backend")
            webview.start()
            _log("webview closed normally (default)")
    except Exception as exc:
        _log("WEBVIEW UNAVAILABLE:\n" + traceback.format_exc())
        # Prefer a clean app-mode window over a raw browser tab.
        if not _open_app_window(url):
            import webbrowser

            _log(f"app-mode unavailable; plain browser for {exc}")
            webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
