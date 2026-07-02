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


def main() -> int:
    _ensure_streams()
    host, port = "127.0.0.1", 17650
    url = f"http://{host}:{port}/"

    server = _make_server(host, port)
    threading.Thread(target=server.run, daemon=True).start()
    ready = _wait_for_http(url + "health")

    if "--selftest" in sys.argv:
        print(f"CLIENT SELFTEST: {'OK' if ready else 'FAIL'} {url}")
        return 0 if ready else 1

    try:
        import webview

        webview.create_window("RETI Studio", url, width=1360, height=900, min_size=(1024, 680))
        webview.start()
    except Exception as exc:
        import webbrowser

        print(f"Desktop window unavailable ({exc}); opening in browser.", file=sys.stderr)
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
