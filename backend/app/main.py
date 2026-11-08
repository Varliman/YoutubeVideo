"""FastAPI web server: video analysis, downloads, and static frontend serving."""

import os
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Query, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .limiter import rate_limiter, validate_youtube_url
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from .services.cleanup import start_periodic_cleanup_thread, delete_file_safely
from .services.youtube import (
    get_ffmpeg_path,
    extract_video_metadata,
    download_video_file,
    download_audio_file,
    download_subtitles_file
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: starts background cleanup tasks."""
    # Ensure temporary storage directory exists
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
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_content_disposition(filename: str) -> str:
    """
    Creates an RFC 5987 / RFC 6266 compliant Content-Disposition header.
    Ensures safe ASCII fallback + UTF-8 filename* for Cyrillic and unicode titles.
    """
    ascii_fallback = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    encoded_utf8 = urllib.parse.quote(filename)
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_utf8}'


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for container orchestrators and monitoring."""
    ffmpeg_bin = get_ffmpeg_path()
    cookies_present = bool(
        settings.COOKIES_FILE or settings.COOKIES_TEXT or settings.COOKIES_FROM_BROWSER
    )
    return HealthResponse(
        status="ok",
        ffmpeg_available=bool(ffmpeg_bin),
        proxy_configured=bool(settings.PROXY_URL),
        cookies_configured=cookies_present,
        storage_dir=str(settings.STORAGE_DIR),
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
