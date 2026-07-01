"""RETI Studio — thin desktop client.

Serves a small local UI and proxies every action to the hosted cloud backend
(video-api.locaith.com) using the customer's access token. No AI key, no ffmpeg,
no rendering happens here — the client only talks to the cloud API.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

CLOUD_URL = os.environ.get("RETI_CLOUD_URL", "https://video-api.locaith.com").rstrip("/")
CLIENT_VERSION = "1.3.1"
GITHUB_REPO = "locaith/reti-studio-installer"


def _parse_ver(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in value.strip().lstrip("vV").split(".")[:3])
    except Exception:
        return (0,)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_ver(latest) > _parse_ver(current)


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    if _frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def _app_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "RETI Studio"
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RETI Studio"


def _config_path() -> Path:
    base = _app_data_dir() if _frozen() else Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "client.json"


def load_token() -> str:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("token", "")
        except Exception:
            return ""
    return ""


def save_token(token: str) -> None:
    _config_path().write_text(json.dumps({"token": token}), encoding="utf-8")


templates = Jinja2Templates(directory=str(_resource_dir() / "templates"))
app = FastAPI()
app.mount("/static", StaticFiles(directory=str(_resource_dir() / "static")), name="static")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {load_token()}"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/update-check")
async def update_check():
    """Ask GitHub for the latest release; report if a newer installer exists."""
    result: dict[str, object] = {"available": False, "current": CLIENT_VERSION}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
            )
        if r.status_code != 200:
            return result
        data = r.json()
        latest = (data.get("tag_name") or "").lstrip("vV")
        want = ".dmg" if sys.platform == "darwin" else ".exe"
        url = next(
            (a["browser_download_url"] for a in data.get("assets", []) if a.get("name", "").lower().endswith(want)),
            None,
        )
        result.update({"latest": latest, "url": url, "available": bool(url) and _is_newer(latest, CLIENT_VERSION)})
    except Exception:
        pass
    return result


@app.post("/do-update")
async def do_update(url: str = Form(...)):
    """Download the new installer and launch it (upgrades in place)."""
    import subprocess
    import tempfile

    try:
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Tải bản cập nhật thất bại.")
        suffix = ".dmg" if sys.platform == "darwin" else ".exe"
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(r.content)
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            os.startfile(path)  # type: ignore[attr-defined]  (Windows)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không mở được bộ cài: {exc}")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, error: str = ""):
    token = load_token()
    if not token:
        return templates.TemplateResponse(request, "setup.html", {"cloud": CLOUD_URL, "error": None})
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            me_resp = await client.get(f"{CLOUD_URL}/api/v1/me", headers=_headers())
            if me_resp.status_code in (401, 403):
                return templates.TemplateResponse(
                    request, "setup.html",
                    {"cloud": CLOUD_URL, "error": "Mã kích hoạt không hợp lệ hoặc đã bị khoá. Nhập lại."},
                )
            me = me_resp.json()
            videos = (await client.get(f"{CLOUD_URL}/api/v1/videos", headers=_headers())).json().get("videos", [])
    except Exception as exc:
        return templates.TemplateResponse(
            request, "setup.html",
            {"cloud": CLOUD_URL, "error": f"Không kết nối được máy chủ. Kiểm tra mạng. ({exc})"},
        )
    return templates.TemplateResponse(request, "home.html", {"me": me, "videos": videos, "error": error or None})


@app.post("/setup")
async def setup(request: Request, token: str = Form(...)):
    token = token.strip()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{CLOUD_URL}/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    except Exception as exc:
        return templates.TemplateResponse(request, "setup.html", {"cloud": CLOUD_URL, "error": f"Không kết nối được máy chủ ({exc})."})
    if resp.status_code == 200:
        save_token(token)
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "setup.html", {"cloud": CLOUD_URL, "error": "Mã kích hoạt không đúng. Kiểm tra lại."})


@app.post("/logout")
def logout():
    save_token("")
    return RedirectResponse("/", status_code=303)


@app.post("/enhance")
async def enhance(
    prompt: str = Form(...),
    duration_seconds: int = Form(8),
    aspect_ratio: str = Form("16:9"),
    video_style: str = Form("cinematic"),
):
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                f"{CLOUD_URL}/api/v1/enhance",
                json={"prompt": prompt, "duration_seconds": duration_seconds,
                      "aspect_ratio": aspect_ratio, "video_style": video_style},
                headers=_headers(),
            )
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as exc:
        return JSONResponse({"detail": f"Lỗi: {exc}"}, status_code=502)


@app.post("/create")
async def create(
    prompt: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    duration_seconds: int = Form(8),
    video_style: str = Form("cinematic"),
    quality: str = Form("standard"),
    voice: str = Form("off"),
    music: str = Form("off"),
    images: list[UploadFile] = File(default=[]),
    logo: UploadFile | None = File(default=None),
):
    data = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration_seconds": str(duration_seconds),
        "video_style": video_style,
        "quality": quality,
        "voice": voice,
        "music": music,
    }
    files = [("images", (f.filename, await f.read(), f.content_type or "image/jpeg")) for f in images if f and f.filename]
    if logo is not None and logo.filename:
        files.append(("logo", (logo.filename, await logo.read(), logo.content_type or "image/png")))
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{CLOUD_URL}/api/v1/videos", data=data, files=files or None, headers=_headers())
    except Exception as exc:
        return RedirectResponse(f"/?error={quote(f'Lỗi kết nối: {exc}')}", status_code=303)
    if resp.status_code == 200:
        return RedirectResponse(f"/video/{resp.json().get('id')}", status_code=303)
    detail = resp.json().get("detail", "Không tạo được video.") if resp.headers.get("content-type", "").startswith("application/json") else "Không tạo được video."
    return RedirectResponse(f"/?error={quote(detail)}", status_code=303)


@app.get("/video/{video_id}", response_class=HTMLResponse)
async def video_page(request: Request, video_id: int):
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}", headers=_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
    return templates.TemplateResponse(request, "detail.html", {"v": resp.json()})


@app.get("/api/video/{video_id}")
async def video_status(video_id: int):
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.get("/api/video/{video_id}/clips")
async def video_clips(video_id: int):
    """Timeline: list all clips of this video (base + extensions)."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}/clips", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.post("/video/{video_id}/extend")
async def video_extend(video_id: int, prompt: str = Form("")):
    """Timeline: add one more Veo clip continuing from the last frame."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{CLOUD_URL}/api/v1/videos/{video_id}/extend",
            data={"prompt": prompt}, headers=_headers(),
        )
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.post("/video/{video_id}/retry")
async def video_retry(video_id: int):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{CLOUD_URL}/api/v1/videos/{video_id}/retry", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.get("/clip/{job_id}/download")
async def clip_download(job_id: int):
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/clips/{job_id}/download", headers=_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Clip chưa sẵn sàng.")
    return Response(content=resp.content, media_type="video/mp4")


@app.get("/video/{video_id}/download")
async def video_download(video_id: int, quality: str = "original"):
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.get(
            f"{CLOUD_URL}/api/v1/videos/{video_id}/download",
            params={"quality": quality}, headers=_headers(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Video chưa sẵn sàng.")
    return Response(content=resp.content, media_type="video/mp4")
