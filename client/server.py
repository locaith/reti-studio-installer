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
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

CLOUD_URL = os.environ.get("RETI_CLOUD_URL", "https://video-api.locaith.com").rstrip("/")
CLIENT_VERSION = "1.6.14"
GITHUB_REPO = "locaith/reti-studio-installer"

# ---- shared HTTP pool ------------------------------------------------------
# One keep-alive connection pool for ALL proxy calls. The old per-request
# `httpx.AsyncClient()` did a fresh TCP+TLS handshake to the cloud on every
# click/poll (~200-500ms each) — the main reason the app felt laggy.
_HTTP: httpx.AsyncClient | None = None


def _pool() -> httpx.AsyncClient:
    global _HTTP
    if _HTTP is None or _HTTP.is_closed:
        _HTTP = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=8.0, read=600.0, write=600.0, pool=10.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=6, max_connections=12,
                                keepalive_expiry=75.0),
        )
    return _HTTP


@asynccontextmanager
async def _pooled():
    yield _pool()  # shared client: do NOT close it per request




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


def load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    _config_path().write_text(json.dumps(cfg), encoding="utf-8")


def load_token() -> str:
    return load_config().get("token", "")


def save_token(token: str) -> None:
    cfg = load_config()
    cfg["token"] = token
    save_config(cfg)


def default_storage_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "RETI Studio"
    return Path.home() / "Videos" / "RETI Studio"


def get_storage_dir() -> Path:
    raw = (load_config().get("storage_dir") or "").strip()
    path = Path(raw) if raw else default_storage_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        path = default_storage_dir()
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_auto_save() -> bool:
    return bool(load_config().get("auto_save", True))


def _safe_name(text: str, limit: int = 48) -> str:
    keep = "".join(c if (c.isalnum() or c in " -_") else " " for c in (text or ""))
    return " ".join(keep.split())[:limit].strip() or "video"


templates = Jinja2Templates(directory=str(_resource_dir() / "templates"))
app = FastAPI()
app.mount("/static", StaticFiles(directory=str(_resource_dir() / "static")), name="static")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {load_token()}"}


async def _me_or_none():
    """Fetch the current customer (name/budget/remaining) or None if not activated/reachable."""
    if not load_token():
        return None
    try:
        async with _pooled() as client:
            r = await client.get(f"{CLOUD_URL}/api/v1/me", headers=_headers())
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _safe_body(r):
    try:
        return r.json()
    except Exception:
        return {"detail": "Lỗi máy chủ."}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/update-check")
async def update_check():
    """Ask GitHub for the latest release; report if a newer installer exists."""
    result: dict[str, object] = {"available": False, "current": CLIENT_VERSION}
    try:
        async with _pooled() as client:
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
        async with _pooled() as client:
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
        async with _pooled() as client:
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
        async with _pooled() as client:
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


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: str = ""):
    return templates.TemplateResponse(
        request, "settings.html",
        {"storage_dir": str(get_storage_dir()), "auto_save": get_auto_save(),
         "default_dir": str(default_storage_dir()), "saved": saved},
    )


@app.post("/settings")
async def settings_save(request: Request, storage_dir: str = Form(""), auto_save: str = Form("off")):
    cfg = load_config()
    chosen = storage_dir.strip()
    if chosen:
        try:
            Path(chosen).mkdir(parents=True, exist_ok=True)
            cfg["storage_dir"] = chosen
        except Exception:
            return templates.TemplateResponse(
                request, "settings.html",
                {"storage_dir": str(get_storage_dir()), "auto_save": get_auto_save(),
                 "default_dir": str(default_storage_dir()),
                 "error": "Không tạo được thư mục này. Kiểm tra lại đường dẫn."},
            )
    cfg["auto_save"] = (auto_save == "on")
    save_config(cfg)
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/save/{video_id}")
async def save_video(video_id: int, quality: str = "original", title: str = Form("")):
    """Download the finished video from the cloud and save it onto THIS machine
    (the customer's own disk), in the configured storage folder."""
    async with _pooled() as client:
        resp = await client.get(
            f"{CLOUD_URL}/api/v1/videos/{video_id}/download",
            params={"quality": quality}, headers=_headers(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Video chưa sẵn sàng để tải.")
    folder = get_storage_dir()
    tag = "" if quality == "original" else f"-{quality}p"
    name = f"{_safe_name(title) or ('reti-' + str(video_id))}-{video_id}{tag}.mp4"
    dest = folder / name
    try:
        dest.write_bytes(resp.content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không lưu được file: {exc}")
    return {"ok": True, "path": str(dest), "folder": str(folder)}


@app.post("/open-folder")
def open_folder():
    folder = get_storage_dir()
    try:
        if sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", str(folder)])
        else:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        return {"ok": True, "folder": str(folder)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request, error: str = ""):
    try:
        async with _pooled() as client:
            r = await client.get(f"{CLOUD_URL}/api/v1/projects", headers=_headers())
        projects = r.json().get("projects", []) if r.status_code == 200 else []
    except Exception as exc:
        projects = []
        error = error or f"Không tải được dự án ({exc})."
    return templates.TemplateResponse(request, "projects.html", {"projects": projects, "error": error or None})


@app.post("/projects")
async def projects_create(request: Request):
    form = await request.form()
    data = {k: str(v) for k, v in form.items()}
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects", data=data, headers=_headers())
    if r.status_code == 200:
        return RedirectResponse(f"/projects/{r.json().get('id')}", status_code=303)
    detail = r.json().get("detail", "Không tạo được dự án.") if r.headers.get("content-type", "").startswith("application/json") else "Lỗi."
    return RedirectResponse(f"/projects?error={quote(detail)}", status_code=303)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int):
    async with _pooled() as client:
        r = await client.get(f"{CLOUD_URL}/api/v1/projects/{project_id}", headers=_headers())
    if r.status_code != 200:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án.")
    return templates.TemplateResponse(request, "project_detail.html", {"p": r.json()})


@app.post("/projects/{project_id}/documents")
async def project_documents(project_id: int, request: Request, text: str = Form(""), files: list[UploadFile] = File(default=[])):
    up = [("files", (f.filename, await f.read(), f.content_type or "application/octet-stream")) for f in files if f and f.filename]
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/documents",
                              data={"text": text}, files=up or None, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/images")
async def project_images(project_id: int, images: list[UploadFile] = File(default=[])):
    up = [("images", (f.filename, await f.read(), f.content_type or "image/jpeg")) for f in images if f and f.filename]
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/images", files=up or None, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/analyze")
async def project_analyze(project_id: int):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/analyze", headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/topics")
async def project_add_topic(project_id: int, title: str = Form(...), angle: str = Form("")):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/topics",
                              data={"title": title, "angle": angle}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/topics/{topic_id}/delete")
async def project_delete_topic(project_id: int, topic_id: int):
    async with _pooled() as client:
        r = await client.delete(f"{CLOUD_URL}/api/v1/projects/{project_id}/topics/{topic_id}", headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/drive/folders")
async def project_drive_folders(project_id: int, link: str = Form(...)):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/drive/folders",
                              data={"link": link}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/drive/import")
async def project_drive_import(project_id: int, folder_id: str = Form(...)):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/drive/import",
                              data={"folder_id": folder_id}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/drive/list-images")
async def project_drive_list_images(project_id: int, folder_id: str = Form(...)):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/drive/list-images",
                              data={"folder_id": folder_id}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/drive/import-one")
async def project_drive_import_one(project_id: int, file_id: str = Form(...), name: str = Form("image.jpg")):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/drive/import-one",
                              data={"file_id": file_id, "name": name}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/drive/mark-synced")
async def project_drive_mark_synced(project_id: int, folder_id: str = Form(...), name: str = Form(""), count: int = Form(0)):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/drive/mark-synced",
                              data={"folder_id": folder_id, "name": name, "count": str(count)}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/video/{video_id}/reassemble")
async def video_reassemble(video_id: int, request: Request):
    body = await request.json()
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/videos/{video_id}/reassemble",
                             json=body, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/video/{video_id}/delete")
async def video_delete(video_id: int):
    async with _pooled() as client:
        r = await client.delete(f"{CLOUD_URL}/api/v1/videos/{video_id}", headers=_headers())
    try:
        data = r.json()
    except Exception:
        data = {"ok": r.status_code < 300}
    return JSONResponse(data, status_code=r.status_code)


@app.post("/projects/{project_id}/topics/{topic_id}/script")
async def project_gen_script(project_id: int, topic_id: int, duration_seconds: int = Form(24)):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/topics/{topic_id}/script",
                              data={"duration_seconds": str(duration_seconds)}, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/topics/{topic_id}/script/save")
async def project_save_script(project_id: int, topic_id: int, request: Request):
    body = await request.json()
    async with _pooled() as client:
        r = await client.put(f"{CLOUD_URL}/api/v1/projects/{project_id}/topics/{topic_id}/script",
                             json=body, headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/projects/{project_id}/topics/{topic_id}/produce")
async def project_produce(project_id: int, topic_id: int, aspect_ratio: str = Form("16:9"),
                          quality: str = Form("standard"), video_style: str = Form("cinematic"),
                          music_url: str = Form(""), music_attr: str = Form("")):
    async with _pooled() as client:
        r = await client.post(f"{CLOUD_URL}/api/v1/projects/{project_id}/topics/{topic_id}/produce",
                              data={"aspect_ratio": aspect_ratio, "quality": quality, "video_style": video_style,
                                    "music_url": music_url, "music_attr": music_attr},
                              headers=_headers())
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/tao-tvc", response_class=HTMLResponse)
async def protvc_page(request: Request):
    me = await _me_or_none()
    if me is None:
        return templates.TemplateResponse(request, "setup.html", {"cloud": CLOUD_URL, "error": None})
    return templates.TemplateResponse(request, "protvc.html", {"me": me})


@app.get("/music/search")
async def music_search(q: str = "", mood: str = "", limit: int = 30):
    async with _pooled() as client:
        r = await client.get(f"{CLOUD_URL}/api/v1/music/search",
                             params={"q": q, "mood": mood, "limit": limit}, headers=_headers())
    return JSONResponse(_safe_body(r), status_code=r.status_code)


@app.post("/protvc/create")
async def protvc_create(drive_link: str = Form(...), name: str = Form("")):
    """One-button flow: create a project (with the Drive link) + one TVC topic, return ids."""
    proj_name = (name or "").strip() or "Dự án TVC"
    async with _pooled() as client:
        pr = await client.post(f"{CLOUD_URL}/api/v1/projects",
                               data={"name": proj_name, "drive_link": drive_link}, headers=_headers())
        if pr.status_code != 200:
            return JSONResponse(_safe_body(pr), status_code=pr.status_code)
        pid = pr.json().get("id")
        tr = await client.post(f"{CLOUD_URL}/api/v1/projects/{pid}/topics",
                               data={"title": "TVC dự án", "angle": ""}, headers=_headers())
        if tr.status_code != 200:
            return JSONResponse(_safe_body(tr), status_code=tr.status_code)
    return JSONResponse({"project_id": pid, "topic_id": tr.json().get("id")})


@app.post("/projects/{project_id}/delete")
async def project_delete(project_id: int):
    async with _pooled() as client:
        await client.delete(f"{CLOUD_URL}/api/v1/projects/{project_id}", headers=_headers())
    return RedirectResponse("/projects", status_code=303)


@app.post("/enhance")
async def enhance(
    prompt: str = Form(...),
    duration_seconds: int = Form(8),
    aspect_ratio: str = Form("16:9"),
    video_style: str = Form("cinematic"),
):
    try:
        async with _pooled() as client:
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
        async with _pooled() as client:
            resp = await client.post(f"{CLOUD_URL}/api/v1/videos", data=data, files=files or None, headers=_headers())
    except Exception as exc:
        return RedirectResponse(f"/?error={quote(f'Lỗi kết nối: {exc}')}", status_code=303)
    if resp.status_code == 200:
        return RedirectResponse(f"/video/{resp.json().get('id')}", status_code=303)
    detail = resp.json().get("detail", "Không tạo được video.") if resp.headers.get("content-type", "").startswith("application/json") else "Không tạo được video."
    return RedirectResponse(f"/?error={quote(detail)}", status_code=303)


@app.get("/video/{video_id}", response_class=HTMLResponse)
async def video_page(request: Request, video_id: int):
    async with _pooled() as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}", headers=_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
    return templates.TemplateResponse(
        request, "detail.html",
        {"v": resp.json(), "auto_save": get_auto_save(), "storage_dir": str(get_storage_dir())},
    )


@app.get("/api/video/{video_id}")
async def video_status(video_id: int):
    async with _pooled() as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.get("/api/video/{video_id}/clips")
async def video_clips(video_id: int):
    """Timeline: list all clips of this video (base + extensions)."""
    async with _pooled() as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}/clips", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.post("/video/{video_id}/extend")
async def video_extend(video_id: int, prompt: str = Form("")):
    """Timeline: add one more Veo clip continuing from the last frame."""
    async with _pooled() as client:
        resp = await client.post(
            f"{CLOUD_URL}/api/v1/videos/{video_id}/extend",
            data={"prompt": prompt}, headers=_headers(),
        )
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.post("/video/{video_id}/retry")
async def video_retry(video_id: int):
    async with _pooled() as client:
        resp = await client.post(f"{CLOUD_URL}/api/v1/videos/{video_id}/retry", headers=_headers())
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.get("/clip/{job_id}/download")
async def clip_download(job_id: int):
    async with _pooled() as client:
        resp = await client.get(f"{CLOUD_URL}/api/v1/clips/{job_id}/download", headers=_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Clip chưa sẵn sàng.")
    return Response(content=resp.content, media_type="video/mp4")


@app.get("/video/{video_id}/download")
async def video_download(video_id: int, quality: str = "original"):
    async with _pooled() as client:
        resp = await client.get(
            f"{CLOUD_URL}/api/v1/videos/{video_id}/download",
            params={"quality": quality}, headers=_headers(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Video chưa sẵn sàng.")
    return Response(content=resp.content, media_type="video/mp4")


def _media_cache_dir() -> Path:
    d = _app_data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _trim_media_cache(keep: int = 15) -> None:
    try:
        files = sorted(_media_cache_dir().glob("video-*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[keep:]:
            f.unlink(missing_ok=True)
    except Exception:
        pass


@app.get("/media/{video_id}")
async def media_stream(video_id: int, refresh: int = 0):
    """Player source: download the finished video ONCE into a local disk cache and
    serve it from there with HTTP Range support (FileResponse) — replays and seeks
    are instant instead of re-streaming the whole file from the cloud every time."""
    f = _media_cache_dir() / f"video-{video_id}.mp4"
    if refresh or not f.exists() or f.stat().st_size == 0:
        async with _pooled() as client:
            resp = await client.get(f"{CLOUD_URL}/api/v1/videos/{video_id}/download", headers=_headers())
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Video chưa sẵn sàng.")
        tmp = f.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(f)
        _trim_media_cache()
    return FileResponse(str(f), media_type="video/mp4")
