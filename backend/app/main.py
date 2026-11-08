"""FastAPI web server: video analysis, downloads, and static frontend serving."""

import os
import urllib.parse
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Query, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .limiter import rate_limiter, validate_youtube_url
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    CheckDownloadResponse,
    PrepareDownloadResponse,
)
from .services.cleanup import start_periodic_cleanup_thread, delete_file_safely
from .services.youtube import (
    get_ffmpeg_path,
    get_nodejs_available,
    get_active_downloads_count,
    check_download_feasibility,
    extract_video_metadata,
    download_video_file,
    download_audio_file,
    download_subtitles_file,
    register_prepared_file,
    pop_prepared_file,
)


def get_process_rss_mb() -> float:
    """
    Measures memory usage. On Linux / Docker (e.g. Render), reads container
    cgroup memory to account for both Python and child FFmpeg processes.
    Falls back to resource.getrusage or psutil on Windows/macOS.
    """
    # 1. cgroup v2 and v1 (Linux container memory covering Python + FFmpeg children)
    for path in (
        "/sys/fs/cgroup/memory.current",
        "/sys/fs/cgroup/memory/memory.usage_in_bytes",
    ):
        try:
            p = Path(path)
            if p.exists():
                val = int(p.read_text().strip())
                return round(val / (1024 * 1024), 1)
        except (FileNotFoundError, ValueError, PermissionError, Exception):
            continue

    # 2. Linux /proc/self/status fallback
    try:
        proc_status = Path("/proc/self/status")
        if proc_status.exists():
            for line in proc_status.read_text().splitlines():
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return round(float(parts[1]) / 1024, 1)
    except Exception:
        pass

    # 3. resource.getrusage (macOS / POSIX fallback)
    try:
        import resource
        import sys
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return round(rusage.ru_maxrss / (1024 * 1024), 1)
        return round(rusage.ru_maxrss / 1024, 1)
    except Exception:
        pass

    # 4. psutil fallback (Windows dev environment)
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except Exception:
        pass

    return 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: starts background cleanup tasks."""
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    # Start periodic storage cleaner (runs every 15 mins, purges files older than 30 mins)
    start_periodic_cleanup_thread(
        settings.STORAGE_DIR,
        settings.CLEANUP_INTERVAL_MINUTES,
        settings.FILE_RETENTION_MINUTES
    )
    yield


app = FastAPI(
    title="YouTube Video Analyzer & Downloader API",
    description="Full-stack YouTube analyzer, metadata extractor, and media downloader.",
    version="1.2.0",
    lifespan=lifespan
)

# CORS setup (disable credentials when wildcard '*' is used to comply with Fetch CORS spec)
_allow_creds = "*" not in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=_allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_content_disposition(filename: str) -> str:
    """
    Creates an RFC 5987 / RFC 6266 compliant Content-Disposition header.
    Ensures safe ASCII fallback + UTF-8 filename* for Cyrillic and unicode titles.
    """
    ascii_fallback = "".join(c if (c.isascii() and (c.isalnum() or c in "._-")) else "_" for c in filename)
    ascii_fallback = ascii_fallback.strip("_") or "download"
    encoded_utf8 = urllib.parse.quote(filename)
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_utf8}'


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Async health check endpoint with Render Free 512MB RAM diagnostics.
    Runs directly on the event loop so Render health probes never time out
    even when worker threads are busy with yt-dlp.
    """
    ffmpeg_bin = get_ffmpeg_path()
    nodejs_ok = get_nodejs_available()
    cookies_present = bool(
        settings.COOKIES_FILE or settings.COOKIES_TEXT or settings.COOKIES_FROM_BROWSER
    )
    rss_mb = get_process_rss_mb()
    if rss_mb < 300:
        oom_risk = "low"
    elif rss_mb < 420:
        oom_risk = "medium"
    else:
        oom_risk = "high"

    return HealthResponse(
        status="ok",
        ffmpeg_available=bool(ffmpeg_bin),
        nodejs_available=nodejs_ok,
        proxy_configured=bool(settings.PROXY_URL),
        cookies_configured=cookies_present,
        storage_dir=str(settings.STORAGE_DIR),
        concurrency_limit=settings.MAX_CONCURRENT_DOWNLOADS,
        max_video_height=settings.MAX_VIDEO_HEIGHT,
        current_active_downloads=get_active_downloads_count(),
        rss_mb=rss_mb,
        oom_risk=oom_risk,
    )


@app.get("/api/check-download", response_model=CheckDownloadResponse)
def check_download(
    request: Request,
    url: str = Query(..., description="YouTube URL"),
    kind: str = Query("video", pattern="^(video|audio|transcript)$"),
    quality: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    lang: Optional[str] = Query(None)
):
    """
    Pre-flight check before initiating heavy file downloads.
    Validates URL, rate limit, server concurrency slot, and actual video accessibility.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(url)

    is_ok, msg, title = check_download_feasibility(
        url=normalized_url,
        kind=kind,
        quality=quality,
        format_str=format,
        lang=lang
    )
    if not is_ok:
        if "Сервер в данный момент" in msg or "Сервер занят" in msg or "429" in msg or "FFmpeg не установлен" in msg:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif "Видео недоступно в качестве" in msg:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif "требует авторизации" in msg:
            status_code = status.HTTP_403_FORBIDDEN
        elif "не найдены" in msg or "удалено" in msg:
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)

    return CheckDownloadResponse(ok=True, message=msg, title=title)


@app.get("/api/prepare-download", response_model=PrepareDownloadResponse)
def prepare_download(
    request: Request,
    url: str = Query(..., description="YouTube URL"),
    kind: str = Query("video", pattern="^(video|audio|transcript)$"),
    quality: str = Query("720p"),
    format: str = Query("mp3"),
    lang: str = Query("ru"),
):
    """
    Two-phase download preparation endpoint:
    Downloads/merges the requested media or subtitle file on the server FIRST via XHR/fetch,
    so any yt-dlp/YouTube error is returned as structured JSON to the frontend UI (preventing
    Firefox/Chrome from navigating to a raw 400/404 browser error page).
    Returns a one-time stream token for native browser download via GET /api/stream/{token}.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(url)

    if kind == "video":
        target_file, filename, mime_type = download_video_file(normalized_url, quality)
    elif kind == "audio":
        target_file, filename, mime_type = download_audio_file(normalized_url, format)
    else:
        target_file, filename, mime_type = download_subtitles_file(normalized_url, lang, format)

    token = register_prepared_file(target_file, filename, mime_type)
    return PrepareDownloadResponse(
        ok=True,
        token=token,
        filename=filename,
        stream_url=f"/api/stream/{token}",
    )


@app.get("/api/stream/{token}")
def stream_prepared_file(token: str, background_tasks: BackgroundTasks):
    """
    Streams an already-prepared file by its one-time token and deletes the temporary job directory
    immediately after streaming completes.
    """
    item = pop_prepared_file(token)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка на скачивание устарела или уже была использована. Пожалуйста, нажмите кнопку скачивания ещё раз."
        )
    target_file, filename, mime_type = item
    background_tasks.add_task(delete_file_safely, target_file.parent)
    return FileResponse(
        path=target_file,
        media_type=mime_type,
        headers={"Content-Disposition": make_content_disposition(filename)},
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_video(payload: AnalyzeRequest, request: Request):
    """
    Analyzes a YouTube URL and returns video metadata, available qualities,
    approximate sizes, and subtitle tracks.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(payload.url)
    return extract_video_metadata(normalized_url)


@app.get("/api/download/video")
def download_video(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube URL"),
    quality: str = Query("720p", pattern="^(1080p|720p|480p|360p|best)$")
):
    """
    Downloads video in specified quality with audio merged and streams it to the client.
    Cleans up server storage immediately after streaming finishes.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(url)

    target_file, filename, mime_type = download_video_file(normalized_url, quality)

    # Schedule deletion of file and job directory after response finishes
    background_tasks.add_task(delete_file_safely, target_file.parent)

    return FileResponse(
        path=target_file,
        media_type=mime_type,
        headers={"Content-Disposition": make_content_disposition(filename)}
    )


@app.get("/api/download/audio")
def download_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube URL"),
    format: str = Query("mp3", pattern="^(mp3|m4a)$")
):
    """
    Downloads audio in MP3 or M4A format and streams it to the client.
    Cleans up server storage immediately after streaming finishes.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(url)

    target_file, filename, mime_type = download_audio_file(normalized_url, format)

    # Schedule deletion of file and job directory after response finishes
    background_tasks.add_task(delete_file_safely, target_file.parent)

    return FileResponse(
        path=target_file,
        media_type=mime_type,
        headers={"Content-Disposition": make_content_disposition(filename)}
    )


@app.get("/api/download/transcript")
def download_transcript(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube URL"),
    lang: str = Query("ru", description="Subtitle language code"),
    format: str = Query("txt", pattern="^(txt|srt)$")
):
    """
    Downloads video transcript or subtitles as clean .txt or standard .srt.
    Cleans up server storage immediately after streaming finishes.
    """
    rate_limiter.check(request)
    normalized_url = validate_youtube_url(url)

    target_file, filename, mime_type = download_subtitles_file(normalized_url, lang, format)

    # Schedule deletion of file and job directory after response finishes
    background_tasks.add_task(delete_file_safely, target_file.parent)

    return FileResponse(
        path=target_file,
        media_type=mime_type,
        headers={"Content-Disposition": make_content_disposition(filename)}
    )


# Mount static frontend
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
