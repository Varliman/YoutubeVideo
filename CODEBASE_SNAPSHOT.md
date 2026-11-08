# ПОЛНЫЙ СНИМОК КОДОВОЙ БАЗЫ: youtube-analyzer-web

## Структура проекта (Дерево каталогов)

`	ext
youtube-analyzer-web/
├── backend
│   ├── app
│   │   ├── services
│   │   │   ├── __init__.py
│   │   │   ├── cleanup.py
│   │   │   └── youtube.py
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── limiter.py
│   │   ├── main.py
│   │   └── schemas.py
│   └── tests
│       └── test_reliability.py
├── frontend
│   ├── app.js
│   ├── index.html
│   └── style.css
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── fly.toml
├── LICENSE
├── package.json
├── README.md
├── render.yaml
└── requirements.txt
`

## Список файлов

1. .env.example (3,014 байт)
2. .gitignore (684 байт)
3. backend/app/__init__.py (94 байт)
4. backend/app/config.py (2,997 байт)
5. backend/app/limiter.py (4,850 байт)
6. backend/app/main.py (9,559 байт)
7. backend/app/schemas.py (2,424 байт)
8. backend/app/services/__init__.py (24 байт)
9. backend/app/services/cleanup.py (2,672 байт)
10. backend/app/services/youtube.py (36,696 байт)
11. backend/tests/test_reliability.py (9,343 байт)
12. docker-compose.yml (717 байт)
13. Dockerfile (1,493 байт)
14. fly.toml (493 байт)
15. frontend/app.js (20,694 байт)
16. frontend/index.html (15,770 байт)
17. frontend/style.css (17,251 байт)
18. LICENSE (1,086 байт)
19. package.json (811 байт)
20. README.md (20,377 байт)
21. render.yaml (528 байт)
22. requirements.txt (135 байт)

---

### Файл: .env.example

`shell
# =====================================================================
# Настройки сервера YouTube Video Analyzer
# =====================================================================

# Порт и хост для привязки веб-сервера
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Прокси для yt-dlp (КРИТИЧНО для деплоя на хостинги Render / Railway / Fly.io / VPS)
# Так как датацентровые IP часто блокируются YouTube (HTTP 429 Too Many Requests),
# укажите здесь рабочий прокси в одном из форматов:
#   1) IP:PORT:LOGIN:PASS (например: 45.153.20.225:11318:FD5sZL:2NqXjY)
#   2) http://LOGIN:PASS@IP:PORT
#   3) socks5://LOGIN:PASS@IP:PORT
# Если деплоите на собственный домашний сервер или резидентный IP, можно оставить пустым:
PROXY_URL=

# Авторизация и Cookies (для приватных видео, 18+ и обхода "Sign in to confirm you're not a bot")
# Вариант 1 (рекомендуемый для хостинга): путь к файлу cookies.txt
COOKIES_FILE=
# Вариант 2: вставить содержимое cookies.txt прямо текстом (удобно для Render/Fly.io env vars)
COOKIES_TEXT=
# Вариант 3 (только для локального ПК): брать куки прямо из установленного браузера (chrome, firefox, edge, brave)
COOKIES_FROM_BROWSER=

# Директория для хранения временных файлов перед отдачей пользователю
STORAGE_DIR=./downloads

# Лимиты безопасности и оптимизация памяти (актуально для Render Free 512 МБ RAM)
# Максимальное количество одновременных процессов скачивания/слияния FFmpeg (для 512 МБ строго 1)
MAX_CONCURRENT_DOWNLOADS=1

# Максимальное разрешение видео по вертикали (720p предотвращает OOM FFmpeg на 512 МБ)
MAX_VIDEO_HEIGHT=720

# Максимальная длительность видео в секундах (14400 сек = 4 часа)
MAX_DURATION_SECONDS=14400

# Максимальный размер скачиваемого файла в мегабайтах (1024 МБ = 1 ГБ)
MAX_FILE_SIZE_MB=1024

# Ограничение частоты запросов с одного IP-адреса в минуту
RATE_LIMIT_PER_MINUTE=30

# Таймаут запросов к YouTube через yt-dlp (в секундах)
YTDLP_TIMEOUT_SECONDS=90

# Настройки периодической очистки временных файлов
CLEANUP_INTERVAL_MINUTES=15
FILE_RETENTION_MINUTES=30

# Разрешенные CORS-домены (через запятую или * для всех)
CORS_ORIGINS=*

`

---

### Файл: .gitignore

`gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
.venv/
env/
ENV/
env.bak/
venv.bak/

# Node / frontend
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# Environment files (CRITICAL: NEVER COMMIT SECRETS)
.env
.env.local
.env.*.local

# Operating System files
.DS_Store
Thumbs.db
desktop.ini

# IDE files
.idea/
.vscode/
*.swp
*.swo

# Media temporary files
*.mp4
*.mp3
*.m4a
*.srt
*.vtt

`

---

### Файл: backend/app/__init__.py

`python
"""YouTube Video Analyzer & Downloader Backend Application Package."""

__version__ = "1.0.0"

`

---

### Файл: backend/app/config.py

`python
"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


def parse_proxy(proxy_str: str) -> str:
    """
    Parses proxy string into a URL format accepted by yt-dlp and requests.
    Supports both 'IP:PORT:LOGIN:PASS' and standard 'http://login:pass@ip:port'.
    """
    if not proxy_str:
        return ""
    proxy_str = proxy_str.strip()
    if proxy_str.startswith("http://") or proxy_str.startswith("https://") or proxy_str.startswith("socks5://"):
        return proxy_str
    parts = proxy_str.split(":")
    if len(parts) == 4:
        ip, port, login, password = parts
        return f"http://{login}:{password}@{ip}:{port}"
    return proxy_str


class Settings:
    """Global application settings."""

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # Proxy settings (crucial for bypassing YouTube datacenter/region blocks)
    _raw_proxy: str = os.getenv("PROXY_URL", os.getenv("PROXY_STRING", "")).strip()
    PROXY_URL: str = parse_proxy(_raw_proxy)
    FORCE_IPV4: bool = os.getenv("FORCE_IPV4", "True").lower() in ("true", "1", "yes")

    # Authentication & Cookies (fixes private, age-restricted, and bot-verification issues)
    COOKIES_FILE: str = os.getenv("COOKIES_FILE", "").strip()
    COOKIES_TEXT: str = os.getenv("COOKIES_TEXT", "").strip()
    COOKIES_FROM_BROWSER: str = os.getenv("COOKIES_FROM_BROWSER", "").strip()

    # Storage & Temporary Files
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "downloads"))).resolve()

    # Limits & Constraints (optimized for Render Free 512MB RAM)
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "1"))
    MAX_VIDEO_HEIGHT: int = int(os.getenv("MAX_VIDEO_HEIGHT", "720"))
    MAX_DURATION_SECONDS: int = int(os.getenv("MAX_DURATION_SECONDS", "14400"))  # 4 hours
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "1024"))  # 1 GB
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    YTDLP_TIMEOUT_SECONDS: int = int(os.getenv("YTDLP_TIMEOUT_SECONDS", "90"))

    # Cleanup scheduler
    CLEANUP_INTERVAL_MINUTES: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "15"))
    FILE_RETENTION_MINUTES: int = int(os.getenv("FILE_RETENTION_MINUTES", "30"))

    # Security & CORS
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


settings = Settings()

# Ensure download storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

`

---

### Файл: backend/app/limiter.py

`python
"""Security validations and in-memory rate limiting."""

import re
import time
from collections import defaultdict
from urllib.parse import urlparse
from fastapi import Request, HTTPException, status
from .config import settings

# YouTube URL regex matching standard watch, shorts, embed, live, youtu.be
YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)([\w-]{11})',
    re.IGNORECASE
)

# Extract video ID
VIDEO_ID_REGEX = re.compile(r'([a-zA-Z0-9_-]{11})')


def validate_youtube_url(url: str) -> str:
    """
    Validates the YouTube URL, prevents SSRF attacks, and returns normalized URL.
    Raises HTTPException(400) if the URL is invalid or unsafe.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL видео не может быть пустым."
        )

    url = url.strip()

    # Prepend https:// if protocol was omitted
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат URL."
        )

    # Allowed hostnames
    allowed_hosts = {
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "youtu.be", "www.youtu.be"
    }

    hostname = (parsed.hostname or "").lower()
    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Разрешены только ссылки на YouTube (youtube.com или youtu.be)."
        )

    # Check for playlists or channels without specific video ID (strict prefix matching)
    path = parsed.path.lower()
    if path == "/playlist" or path.startswith("/playlist/") or (parsed.query and "list=" in parsed.query and "v=" not in parsed.query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Скачивание плейлистов целиком не поддерживается. Пожалуйста, укажите ссылку на конкретное видео."
        )
    if path.startswith("/@") or path.startswith("/channel/") or path.startswith("/c/") or path.startswith("/user/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылки на каналы не поддерживаются. Пожалуйста, укажите ссылку на конкретное видео."
        )

    # Validate pattern and extract ID
    match = YOUTUBE_URL_REGEX.match(url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось распознать корректный идентификатор видео YouTube в ссылке."
        )

    video_id = match.group(5)
    # Return normalized canonical URL
    return f"https://www.youtube.com/watch?v={video_id}"


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter per client IP."""

    def __init__(self, limit_per_minute: int = 30):
        self.limit = limit_per_minute
        self.window = 60.0  # seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extracts client IP, respecting forward headers from proxies like Render/Cloudflare."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request):
        """Checks rate limit for current request; raises HTTPException(429) if exceeded."""
        if self.limit <= 0:
            return  # Rate limiting disabled

        ip = self._get_client_ip(request)
        now = time.time()
        timestamps = self.requests[ip]

        # Evict timestamps outside current 60s sliding window
        valid_timestamps = [t for t in timestamps if now - t < self.window]
        self.requests[ip] = valid_timestamps

        if len(valid_timestamps) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много запросов. Лимит: {self.limit} в минуту с одного IP. Подождите немного."
            )

        valid_timestamps.append(now)


rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_PER_MINUTE)

`

---

### Файл: backend/app/main.py

`python
"""FastAPI web server: video analysis, downloads, and static frontend serving."""

import os
import urllib.parse
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Query, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .limiter import rate_limiter, validate_youtube_url
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    CheckDownloadResponse,
)
from .services.cleanup import start_periodic_cleanup_thread, delete_file_safely
from .services.youtube import (
    get_ffmpeg_path,
    get_active_downloads_count,
    check_download_feasibility,
    extract_video_metadata,
    download_video_file,
    download_audio_file,
    download_subtitles_file,
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
    """Health check endpoint with Render Free 512MB RAM diagnostics."""
    ffmpeg_bin = get_ffmpeg_path()
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
    Returns video title and status, preventing silent browser download failures.
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
        if "Сервер в данный момент" in msg or "Сервер занят" in msg:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif "Видео недоступно в качестве" in msg:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)

    return CheckDownloadResponse(ok=True, message=msg, title=title)


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

`

---

### Файл: backend/app/schemas.py

`python
"""Pydantic data models for request and response serialization."""

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Payload to request video analysis."""
    url: str = Field(..., description="YouTube video URL (watch, shorts, youtu.be, embed)")


class FormatItem(BaseModel):
    """Raw format details extracted by yt-dlp."""
    format_id: str
    ext: str
    resolution: str
    fps: Optional[float] = None
    filesize: Optional[int] = None
    filesize_str: str
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    note: Optional[str] = None


class VideoOption(BaseModel):
    """Preset video download choice with estimated size."""
    quality: str  # 1080p, 720p, 480p, 360p, best
    label: str
    ext: str = "mp4"
    filesize_approx_mb: Optional[float] = None
    filesize_str: str
    download_url: str


class AudioOption(BaseModel):
    """Preset audio download choice with estimated size."""
    format: str  # mp3, m4a
    label: str
    bitrate_kbps: int
    filesize_approx_mb: Optional[float] = None
    filesize_str: str
    download_url: str


class SubtitleOption(BaseModel):
    """Available transcript/subtitle language."""
    lang: str
    name: str
    is_auto: bool
    txt_url: str
    srt_url: str


class AnalyzeResponse(BaseModel):
    """Comprehensive video metadata and download options."""
    id: str
    title: str
    channel: str
    channel_url: Optional[str] = None
    duration: int
    duration_str: str
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    thumbnail: Optional[str] = None
    original_url: str
    description: Optional[str] = None
    video_options: list[VideoOption]
    audio_options: list[AudioOption]
    subtitle_options: list[SubtitleOption]
    all_formats: list[FormatItem]


class CheckDownloadResponse(BaseModel):
    """Pre-check validation response prior to launching heavy downloads."""
    ok: bool
    title: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response with Render Free 512MB RAM diagnostics."""
    status: str
    ffmpeg_available: bool
    proxy_configured: bool
    cookies_configured: bool
    storage_dir: str
    concurrency_limit: int
    max_video_height: int
    current_active_downloads: int
    rss_mb: float
    oom_risk: str  # "low" | "medium" | "high"

`

---

### Файл: backend/app/services/__init__.py

`python
"""Services package."""

`

---

### Файл: backend/app/services/cleanup.py

`python
"""Temporary file cleanup utilities to prevent disk exhaustion."""

import os
import time
import shutil
import logging
import threading
from pathlib import Path

logger = logging.getLogger("cleanup")

# Protected system files that must NEVER be deleted by cleanup (module-level constant)
PROTECTED_FILENAMES = {"cookies.txt", ".gitkeep", "README.md"}


def delete_file_safely(file_or_dir_path: str | Path):
    """Safely removes a file or directory without raising exceptions."""
    try:
        p = Path(file_or_dir_path)
        if p.is_file():
            p.unlink(missing_ok=True)
            logger.info(f"Cleaned up temporary file: {p.name}")
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {p.name}")
    except Exception as e:
        logger.warning(f"Error deleting path {file_or_dir_path}: {e}")


def cleanup_old_files(storage_dir: Path, max_age_seconds: int):
    """Deletes files and directories inside storage_dir older than max_age_seconds."""
    if not storage_dir.exists():
        return

    now = time.time()
    try:
        for entry in storage_dir.iterdir():
            if entry.name in PROTECTED_FILENAMES:
                continue

            try:
                stat = entry.stat()
                age = now - stat.st_mtime
                if age > max_age_seconds:
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink(missing_ok=True)
                    logger.info(f"Purged expired temporary item: {entry.name} (age: {int(age)}s)")
            except Exception as e:
                logger.debug(f"Could not stat/delete {entry}: {e}")
    except Exception as e:
        logger.error(f"Error scanning storage dir for cleanup: {e}")


def start_periodic_cleanup_thread(storage_dir: Path, interval_minutes: int, retention_minutes: int):
    """Starts a daemon thread that periodically purges old temporary download files."""
    def worker():
        interval_secs = max(interval_minutes, 1) * 60
        retention_secs = max(retention_minutes, 1) * 60
        while True:
            try:
                time.sleep(interval_secs)
                cleanup_old_files(storage_dir, retention_secs)
            except Exception as e:
                logger.error(f"Periodic cleanup worker error: {e}")

    thread = threading.Thread(target=worker, daemon=True, name="storage-cleanup")
    thread.start()
    logger.info(
        f"Started storage cleanup worker (runs every {interval_minutes}m, "
        f"retention: {retention_minutes}m)"
    )

`

---

### Файл: backend/app/services/youtube.py

`python
"""YouTube extraction and media downloading service using yt-dlp and ffmpeg."""

import os
import re
import time
import uuid
import shutil
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple
import yt_dlp
from fastapi import HTTPException, status
from ..config import settings
from ..schemas import (
    AnalyzeResponse,
    VideoOption,
    AudioOption,
    SubtitleOption,
    FormatItem
)

logger = logging.getLogger("youtube-service")


def sanitize_error_message(error: Exception | str) -> str:
    """Strips passwords and sensitive credentials from error messages and proxy URLs."""
    msg = str(error)
    # Strip user:password credentials from URLs (e.g. http://login:pass@host:port)
    msg = re.sub(r'://([^:/\s]+):([^@/\s]+)@', r'://\1:***@', msg)
    # Optionally mask bare proxy password if it is at least 6 characters and bounded
    if getattr(settings, "PROXY_URL", None):
        match = re.search(r'://([^:/\s]+):([^@/\s]+)@', settings.PROXY_URL)
        if match:
            pwd = match.group(2)
            if pwd and len(pwd) >= 6:
                msg = re.sub(rf'(?<!\w){re.escape(pwd)}(?!\w)', '***', msg)
    return msg


_download_semaphore = threading.Semaphore(settings.MAX_CONCURRENT_DOWNLOADS)
_active_downloads_count = 0
_active_downloads_lock = threading.Lock()

# 60-second in-memory metadata cache to prevent redundant extract_info calls
_INFO_CACHE: dict[str, Tuple[float, dict]] = {}
_INFO_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 60.0


def get_cached_or_extract_info(url: str, extra_opts: Optional[dict] = None) -> dict:
    """
    Retrieves video info dictionary from in-memory cache or extracts via yt-dlp.
    Cached for 60 seconds to eliminate redundant network extraction between pre-check and download.
    """
    now = time.time()
    with _INFO_CACHE_LOCK:
        # Periodic purge of entries older than 120s
        expired = [k for k, (ts, _) in _INFO_CACHE.items() if now - ts > 120]
        for k in expired:
            _INFO_CACHE.pop(k, None)

        cached = _INFO_CACHE.get(url)
        if cached and (now - cached[0] < _CACHE_TTL_SECONDS):
            return cached[1]

    opts = get_ydl_base_opts({
        "skip_download": True,
        "ignore_no_formats_error": True,
        "retries": 3,
        "extractor_retries": 3,
    })
    if extra_opts:
        opts.update(extra_opts)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    with _INFO_CACHE_LOCK:
        _INFO_CACHE[url] = (time.time(), info)

    return info


def get_active_downloads_count() -> int:
    """Returns the number of currently active download jobs."""
    with _active_downloads_lock:
        return _active_downloads_count


class DownloadSlot:
    """
    Context manager for acquiring a download concurrency slot.
    Protects 512 MB RAM environments against OOM SIGKILL by rejecting concurrent requests with 503.
    """
    def __init__(self, blocking: bool = False, timeout: Optional[float] = None):
        self.blocking = blocking
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        global _active_downloads_count
        if self.blocking:
            self.acquired = _download_semaphore.acquire(blocking=True, timeout=self.timeout)
        else:
            self.acquired = _download_semaphore.acquire(blocking=False)

        if not self.acquired:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Сервер в данный момент выполняет другую загрузку. "
                    f"Из-за лимита оперативной памяти (512 МБ RAM) загрузки выполняются строго по очереди "
                    f"(лимит: {settings.MAX_CONCURRENT_DOWNLOADS} одновременный процесс). "
                    f"Слот мог быть занят сразу после предварительной проверки. "
                    f"Пожалуйста, повторите попытку через несколько минут."
                )
            )
        with _active_downloads_lock:
            _active_downloads_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _active_downloads_count
        if self.acquired:
            with _active_downloads_lock:
                _active_downloads_count = max(0, _active_downloads_count - 1)
            _download_semaphore.release()


def check_download_feasibility(
    url: str,
    kind: str,
    quality: Optional[str] = None,
    format_str: Optional[str] = None,
    lang: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Pre-flight check before initiating heavy file downloads.
    1. Checks server limits (FFmpeg, active download semaphore).
    2. Checks video accessibility (extracts/uses cached metadata, detects private/429/403).
    3. Checks format/quality availability (verifies video height <= requested quality).
    Returns: (is_ok: bool, message: str, title: Optional[str])
    """
    # 1. Server constraints - cheap
    if not get_ffmpeg_path() and (kind == "video" or format_str == "mp3"):
        return False, "FFmpeg не установлен на сервере. Слияние аудио и видео невозможно.", None

    if kind in ("video", "audio") and get_active_downloads_count() >= settings.MAX_CONCURRENT_DOWNLOADS:
        return (
            False,
            f"Сервер занят другой загрузкой. Из-за лимита памяти (512 МБ) "
            f"загрузки выполняются строго по очереди. Попробуйте через несколько минут.",
            None
        )

    # 2. Real video accessibility check - uses 60s in-memory cache
    try:
        info = get_cached_or_extract_info(url)
    except yt_dlp.utils.DownloadError as e:
        err_msg = sanitize_error_message(e)
        if "429" in err_msg:
            return False, "YouTube заблокировал IP-адрес сервера (HTTP 429 Too Many Requests).", None
        elif "Private video" in err_msg or "Sign in" in err_msg:
            return False, "Видео требует авторизации YouTube (приватное или 18+).", None
        elif "Video unavailable" in err_msg:
            return False, "Видео недоступно, удалено или заблокировано правообладателем.", None
        return False, f"Ошибка доступа к видео: {err_msg}", None
    except Exception as e:
        return False, f"Ошибка проверки видео: {sanitize_error_message(e)}", None

    title = info.get("title", "")

    # 3. Check requested quality availability
    if kind == "video" and quality:
        cap = settings.MAX_VIDEO_HEIGHT or 1080
        quality_map = {"best": cap, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
        target_h = quality_map.get(quality, cap)
        want = min(target_h, cap)
        formats = info.get("formats", [])
        heights = [f.get("height") or 0 for f in formats]
        if not any(0 < h <= want for h in heights):
            return False, f"Видео недоступно в качестве ≤{want}p.", title

    elif kind == "transcript" and lang:
        manual = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}
        available_langs = set(manual.keys()) | set(auto.keys()) | {"ru", "en"}
        if lang not in available_langs:
            return False, f"Субтитры для языка '{lang}' не найдены у данного видео.", title

    clean_title = sanitize_filename(title, max_len=80)
    return True, f"Готово: {clean_title}", title


def _build_format_selector(quality: str, max_height_cap: Optional[int] = None) -> str:
    """
    Builds a robust yt-dlp format selector with strict downward cascading.
    Guarantees no trailing unconstrained '/best' or unconstrained '/worst' that could pick 4K/1080p.
    Enforces max_height_cap (e.g. 720p for Render Free 512MB RAM).
    """
    quality_height_map = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
    target_h = quality_height_map.get(quality)
    if max_height_cap:
        if target_h and target_h > max_height_cap:
            target_h = max_height_cap
        elif quality == "best":
            target_h = max_height_cap

    if target_h is None:
        return "bestvideo+bestaudio/best"

    # Strictly under target_h: no branch can exceed target_h
    steps = [h for h in (1080, 720, 480, 360) if h <= target_h]
    parts = []
    for h in steps:
        parts.append(f"bestvideo[height<={h}]+bestaudio")
        parts.append(f"best[height<={h}]")
    # worst is also strictly bounded by target_h - otherwise it could pick 4K
    parts.append(f"worstvideo[height<={target_h}]+worstaudio")
    parts.append(f"worst[height<={target_h}]")
    return "/".join(parts)


def get_ffmpeg_path() -> Optional[str]:
    """Finds ffmpeg executable in system PATH or via imageio_ffmpeg."""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Removes invalid characters and restricts length for safe filesystem use."""
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    clean = name.strip("._-")
    return clean[:max_len] if clean else "video"


def format_bytes(size_bytes: Optional[int | float]) -> str:
    """Formats bytes to human-readable size string (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "Размер уточняется"
    size_mb = size_bytes / (1024 * 1024)
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} ГБ"
    elif size_mb >= 1:
        return f"{size_mb:.1f} МБ"
    else:
        return f"{size_bytes / 1024:.0f} КБ"


def format_duration(seconds: Optional[int | float]) -> str:
    """Formats duration in seconds to HH:MM:SS or MM:SS string."""
    if not seconds:
        return "00:00"
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_ydl_base_opts(extra_opts: Optional[dict] = None) -> dict:
    """Constructs base yt-dlp options including proxy, cookies, retries, and timeouts."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "socket_timeout": settings.YTDLP_TIMEOUT_SECONDS,
        "retries": 10,
        "fragment_retries": 10,
        "continuedl": True,
        "http_chunk_size": 10485760,  # 10MB chunk size prevents YouTube throttling
        "extractor_args": {
            "youtube": {
                # Using mweb, web, and tv (avoiding ios which requires strict po_token)
                "player_client": ["mweb", "web", "tv"],
            }
        },
    }

    # Force IPv4 if enabled to prevent cloud IPv6 429 rate-limiting
    if getattr(settings, "FORCE_IPV4", True):
        opts["source_address"] = "0.0.0.0"

    if settings.PROXY_URL:
        opts["proxy"] = settings.PROXY_URL

    # Authentication & Cookies support (fixes private, age-restricted, and bot check issues)
    if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
        opts["cookiefile"] = settings.COOKIES_FILE
    elif settings.COOKIES_TEXT:
        cookies_path = settings.STORAGE_DIR / "cookies.txt"
        if not cookies_path.exists():
            cookies_path.write_text(settings.COOKIES_TEXT.strip(), encoding="utf-8")
        opts["cookiefile"] = str(cookies_path)
    elif settings.COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (settings.COOKIES_FROM_BROWSER, None, None, None)

    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg_bin) if os.path.isfile(ffmpeg_bin) else ffmpeg_bin

    if extra_opts:
        opts.update(extra_opts)

    return opts


def extract_video_metadata(url: str) -> AnalyzeResponse:
    """
    Extracts complete metadata, available formats, estimated sizes,
    and available subtitle tracks for a YouTube video.
    """
    try:
        meta = get_cached_or_extract_info(url)
    except yt_dlp.utils.DownloadError as e:
        error_msg = sanitize_error_message(e)
        if "429" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "YouTube заблокировал IP-адрес сервера (HTTP 429 Too Many Requests). "
                    "Для работы на серверах хостинга требуется настроить PROXY_URL в .env."
                )
            )
        elif "Private video" in error_msg or "Sign in" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Видео требует авторизации YouTube (приватное видео, возрастное ограничение 18+ "
                    "или проверка бота 'Sign in to confirm you're not a bot'). "
                    "Для доступа подключите cookies вашего аккаунта (укажите COOKIES_FILE, COOKIES_TEXT "
                    "или COOKIES_FROM_BROWSER в настройках .env сервера)."
                )
            )
        elif "Requested format is not available" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Запрошенный формат недоступен. Это часто происходит, если видео является прямой "
                    "трансляцией (Live), запланированной премьерой или YouTube ограничил отдачу форматов "
                    "для данного региона/клиента."
                )
            )
        elif "Video unavailable" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Видео недоступно, удалено или заблокировано правообладателем."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка yt-dlp при анализе видео: {error_msg}"
            )
    except Exception as e:
        sanitized_err = sanitize_error_message(e)
        logger.error(f"Unexpected extraction error for {url}: {sanitized_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка при извлечении метаданных: {sanitized_err}"
        )

    duration = meta.get("duration") or 0
    if duration > settings.MAX_DURATION_SECONDS:
        max_hours = settings.MAX_DURATION_SECONDS // 3600
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Длительность видео ({format_duration(duration)}) превышает допустимый лимит сервера ({max_hours} ч)."
        )

    # 1. Parse raw formats for tech view
    all_formats: list[FormatItem] = []
    formats = meta.get("formats", [])

    if not formats:
        if meta.get("is_live"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Это видео является прямым эфиром (Live stream). Скачивание форматов станет доступно после завершения трансляции и обработки архива YouTube."
            )
        elif meta.get("live_status") == "is_upcoming":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Это видео является запланированной премьерой или будущей трансляцией. Скачивание пока недоступно."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YouTube не вернул доступных форматов для данного видео (возможно, трансляция ещё обрабатывается, видео заблокировано в регионе или требует авторизации)."
            )
    for f in formats:
        f_id = str(f.get("format_id", ""))
        ext = f.get("ext", "mp4")
        res = f.get("resolution") or (f"{f.get('width')}x{f.get('height')}" if f.get('width') else "audio only")
        fps = f.get("fps")
        filesize = f.get("filesize") or f.get("filesize_approx")
        vcodec = f.get("vcodec") if f.get("vcodec") != "none" else None
        acodec = f.get("acodec") if f.get("acodec") != "none" else None
        note = f.get("format_note")

        all_formats.append(
            FormatItem(
                format_id=f_id,
                ext=ext,
                resolution=res,
                fps=fps,
                filesize=filesize,
                filesize_str=format_bytes(filesize),
                vcodec=vcodec,
                acodec=acodec,
                note=note,
            )
        )

    # 2. Compute audio estimated size
    # Average audio stream is ~128-160 kbps = 20 KB/s
    audio_est_bytes = duration * (160 * 1024 / 8) if duration > 0 else 0

    # 3. Build preset Video Options: 1080p, 720p, 480p, 360p, best
    if settings.MAX_VIDEO_HEIGHT and settings.MAX_VIDEO_HEIGHT < 1080:
        quality_specs = [
            ("best", f"Наилучшее доступное качество (до {settings.MAX_VIDEO_HEIGHT}p, Render Free)", settings.MAX_VIDEO_HEIGHT),
            ("1080p", f"Full HD 1080p (MP4) — недоступно (лимит {settings.MAX_VIDEO_HEIGHT}p на сервере)", 1080),
            ("720p", "HD 720p (MP4)", 720),
            ("480p", "SD 480p (MP4)", 480),
            ("360p", "Низкое 360p (MP4)", 360),
        ]
    else:
        quality_specs = [
            ("best", "Наилучшее доступное качество (Original/Best)", None),
            ("1080p", "Full HD 1080p (MP4)", 1080),
            ("720p", "HD 720p (MP4)", 720),
            ("480p", "SD 480p (MP4)", 480),
            ("360p", "Низкое 360p (MP4)", 360),
        ]

    video_options: list[VideoOption] = []
    for q_key, q_label, max_h in quality_specs:
        # Find matching formats to estimate combined size
        best_match_size = None
        for f in formats:
            h = f.get("height")
            if max_h is None or (h and h <= max_h):
                f_size = f.get("filesize") or f.get("filesize_approx")
                if f_size and (best_match_size is None or f_size > best_match_size):
                    best_match_size = f_size

        if not best_match_size and duration > 0:
            # Fallback estimation based on typical bitrates
            bitrate_map = {1080: 3500, 720: 2000, 480: 1000, 360: 600}
            target_kbps = bitrate_map.get(max_h, 4500) if max_h else 4500
            best_match_size = duration * (target_kbps * 1024 / 8)

        total_bytes = (best_match_size or 0) + (audio_est_bytes if max_h else 0)
        total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes > 0 else None

        video_options.append(
            VideoOption(
                quality=q_key,
                label=q_label,
                ext="mp4",
                filesize_approx_mb=total_mb,
                filesize_str=format_bytes(total_bytes) if total_bytes else "Размер уточняется",
                download_url=f"/api/download/video?url={url}&quality={q_key}",
            )
        )

    # 4. Build preset Audio Options: MP3 (320k) and M4A
    mp3_bytes = duration * (320 * 1024 / 8) if duration > 0 else None
    m4a_bytes = duration * (128 * 1024 / 8) if duration > 0 else None

    audio_options: list[AudioOption] = [
        AudioOption(
            format="mp3",
            label="Аудио MP3 (Высокое качество, 320 kbps)",
            bitrate_kbps=320,
            filesize_approx_mb=round(mp3_bytes / (1024 * 1024), 1) if mp3_bytes else None,
            filesize_str=format_bytes(mp3_bytes) if mp3_bytes else "Размер уточняется",
            download_url=f"/api/download/audio?url={url}&format=mp3",
        ),
        AudioOption(
            format="m4a",
            label="Аудио M4A (Оригинальный AAC-поток YouTube)",
            bitrate_kbps=128,
            filesize_approx_mb=round(m4a_bytes / (1024 * 1024), 1) if m4a_bytes else None,
            filesize_str=format_bytes(m4a_bytes) if m4a_bytes else "Размер уточняется",
            download_url=f"/api/download/audio?url={url}&format=m4a",
        ),
    ]

    # 5. Build Subtitle / Transcript options
    subtitle_options: list[SubtitleOption] = []
    seen_langs = set()

    # Manual subtitles first
    manual_subs = meta.get("subtitles") or {}
    for lang, track_list in manual_subs.items():
        name = track_list[0].get("name", lang) if track_list else lang
        seen_langs.add(lang)
        subtitle_options.append(
            SubtitleOption(
                lang=lang,
                name=f"{name} (ручные)",
                is_auto=False,
                txt_url=f"/api/download/transcript?url={url}&lang={lang}&format=txt",
                srt_url=f"/api/download/transcript?url={url}&lang={lang}&format=srt",
            )
        )

    # Automatic captions next
    auto_subs = meta.get("automatic_captions") or {}
    for lang, track_list in auto_subs.items():
        if lang not in seen_langs:
            name = track_list[0].get("name", lang) if track_list else lang
            subtitle_options.append(
                SubtitleOption(
                    lang=lang,
                    name=f"{name} (автогенерация)",
                    is_auto=True,
                    txt_url=f"/api/download/transcript?url={url}&lang={lang}&format=txt",
                    srt_url=f"/api/download/transcript?url={url}&lang={lang}&format=srt",
                )
            )

    # Format upload date (e.g. 20240412 -> 2024-04-12)
    raw_date = meta.get("upload_date") or ""
    formatted_date = None
    if len(raw_date) == 8:
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"

    return AnalyzeResponse(
        id=meta.get("id", ""),
        title=meta.get("title", "Без названия"),
        channel=meta.get("channel", "Неизвестный канал"),
        channel_url=meta.get("channel_url") or meta.get("uploader_url"),
        duration=duration,
        duration_str=format_duration(duration),
        upload_date=formatted_date,
        view_count=meta.get("view_count"),
        thumbnail=meta.get("thumbnail"),
        original_url=url,
        description=meta.get("description", "")[:1500],
        video_options=video_options,
        audio_options=audio_options,
        subtitle_options=subtitle_options,
        all_formats=all_formats,
    )


def download_video_file(url: str, quality: str = "720p") -> Tuple[Path, str, str]:
    """
    Downloads video using yt-dlp with the specified quality and merges with audio into MP4.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
    # Enforce MAX_VIDEO_HEIGHT constraint if requested quality exceeds it
    if settings.MAX_VIDEO_HEIGHT and quality == "1080p" and settings.MAX_VIDEO_HEIGHT < 1080:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Качество 1080p отключено из-за ограничения памяти сервера (512 МБ RAM). "
                f"Максимальное допустимое разрешение: {settings.MAX_VIDEO_HEIGHT}p."
            )
        )

    # Fail-fast check for FFmpeg before downloading
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "FFmpeg не обнаружен на сервере. Для объединения раздельных видео- и аудиопотоков "
                "в формат MP4 требуется установленный FFmpeg."
            )
        )

    with DownloadSlot():
        unique_job_id = f"video_{uuid.uuid4().hex[:10]}"
        job_dir = settings.STORAGE_DIR / unique_job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        fmt = _build_format_selector(quality, settings.MAX_VIDEO_HEIGHT)
        out_template = str(job_dir / "%(title)s_%(resolution)s.%(ext)s")

        ydl_opts = get_ydl_base_opts({
            "format": fmt,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
        })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = sanitize_filename(info.get("title", "video"))
        except yt_dlp.utils.DownloadError as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            if "Requested format is not available" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Видео недоступно в качестве ≤{settings.MAX_VIDEO_HEIGHT}p."
                )
            logger.error(f"Error downloading video {url} [{quality}]: {sanitized_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось скачать видео: {sanitized_err}"
            )
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            logger.error(f"Error downloading video {url} [{quality}]: {sanitized_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось скачать видео: {sanitized_err}"
            )

        # Belt-and-suspenders check: ensure downloaded resolution did not exceed MAX_VIDEO_HEIGHT
        downloaded_height = info.get("height") or 0
        if settings.MAX_VIDEO_HEIGHT and downloaded_height > settings.MAX_VIDEO_HEIGHT + 1:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Скачанное разрешение ({downloaded_height}p) превышает лимит сервера ({settings.MAX_VIDEO_HEIGHT}p)."
            )

        # Locate generated output file
        downloaded_files = [f for f in job_dir.glob("*.mp4")]
        if not downloaded_files:
            # Fallback search for any media file
            downloaded_files = [f for f in job_dir.iterdir() if f.is_file()]

        if not downloaded_files:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Результирующий видеофайл не был создан."
            )

        target_file = downloaded_files[0]
        file_size_mb = target_file.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер скачанного файла ({file_size_mb:.1f} МБ) превышает лимит сервера ({settings.MAX_FILE_SIZE_MB} МБ)."
            )

        download_filename = f"{title}_{quality}.mp4"
        return target_file, download_filename, "video/mp4"


def download_audio_file(url: str, audio_format: str = "mp3") -> Tuple[Path, str, str]:
    """
    Downloads audio using yt-dlp, extracting to MP3 or M4A.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
    if audio_format.lower() == "mp3":
        ffmpeg_bin = get_ffmpeg_path()
        if not ffmpeg_bin:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "FFmpeg не обнаружен на сервере. Для конвертации аудио в формат MP3 (320 kbps) "
                    "требуется FFmpeg. Вы можете скачать аудио в формате M4A без перекодирования."
                )
            )

    with DownloadSlot():
        unique_job_id = f"audio_{uuid.uuid4().hex[:10]}"
        job_dir = settings.STORAGE_DIR / unique_job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        out_template = str(job_dir / "%(title)s.%(ext)s")

        if audio_format.lower() == "mp3":
            ydl_opts = get_ydl_base_opts({
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }],
            })
            expected_ext = ".mp3"
            mime_type = "audio/mpeg"
        else:  # m4a
            ydl_opts = get_ydl_base_opts({
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": out_template,
            })
            expected_ext = ".m4a"
            mime_type = "audio/mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = sanitize_filename(info.get("title", "audio"))
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            logger.error(f"Error downloading audio {url} [{audio_format}]: {sanitized_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось скачать аудио: {sanitized_err}"
            )

        # Locate generated output file
        downloaded_files = [f for f in job_dir.glob(f"*{expected_ext}")]
        if not downloaded_files:
            downloaded_files = [f for f in job_dir.iterdir() if f.is_file()]

        if not downloaded_files:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Результирующий аудиофайл не был создан."
            )

        target_file = downloaded_files[0]
        download_filename = f"{title}.{audio_format.lower()}"
        return target_file, download_filename, mime_type


def srt_to_clean_txt(srt_content: str) -> str:
    """
    Cleans an SRT string into pure legible text:
    removes numeric indexes, timestamps, HTML tags, and duplicate consecutive lines.
    Preserves natural repetition of lyrics and dialogue while removing rolling caption artifacts.
    """
    lines = []
    prev_line = ""
    for raw_line in srt_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip numeric index lines
        if re.match(r"^\d+$", line):
            continue
        # Skip timestamp lines (00:00:01,000 --> 00:00:04,000)
        if re.match(r"\d{2}:\d{2}:\d{2}", line):
            continue
        # Remove HTML-like markup (font, b, i, color, etc.)
        clean = re.sub(r"<[^>]+>", "", line).strip()
        # Deduplicate ONLY consecutive identical lines (YouTube auto-subtitles rolling artifact),
        # preserving recurring phrases, songs, and dialogue throughout the video
        if clean and clean != prev_line:
            lines.append(clean)
            prev_line = clean

    return "\n".join(lines)


def download_subtitles_file(url: str, lang: str = "ru", format_type: str = "txt") -> Tuple[Path, str, str]:
    """
    Extracts subtitles (manual first, then auto) using yt-dlp.
    Outputs clean .txt (without timestamps/duplicates) or standard .srt.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
    with DownloadSlot():
        unique_job_id = f"subs_{uuid.uuid4().hex[:10]}"
        job_dir = settings.STORAGE_DIR / unique_job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        out_template = str(job_dir / "subtitles")

        # First attempt: manual subtitles
        ydl_opts_manual = get_ydl_base_opts({
            "skip_download": True,
            "writesubtitles": True,
            "subtitleslangs": [lang, "ru", "en"],
            "subtitlesformat": "srt",
            "outtmpl": out_template,
        })

        found_srt = None
        title = "subtitles"

        try:
            with yt_dlp.YoutubeDL(ydl_opts_manual) as ydl:
                info = ydl.extract_info(url, download=True)
                title = sanitize_filename(info.get("title", "transcript"))
        except Exception as e:
            logger.warning(f"Error checking manual subs: {sanitize_error_message(e)}")

        # Check for manual subs file
        srt_candidates = list(job_dir.glob("*.srt")) + list(job_dir.glob("*.vtt"))
        if srt_candidates:
            found_srt = srt_candidates[0]

        # Second attempt: auto-generated captions if manual not found
        if not found_srt:
            ydl_opts_auto = get_ydl_base_opts({
                "skip_download": True,
                "writeautomaticsub": True,
                "subtitleslangs": [lang, "ru", "en"],
                "subtitlesformat": "srt",
                "outtmpl": out_template,
            })
            try:
                with yt_dlp.YoutubeDL(ydl_opts_auto) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = sanitize_filename(info.get("title", "transcript"))
            except Exception as e:
                logger.warning(f"Error checking auto subs: {sanitize_error_message(e)}")

            srt_candidates = list(job_dir.glob("*.srt")) + list(job_dir.glob("*.vtt"))
            if srt_candidates:
                found_srt = srt_candidates[0]

        if not found_srt:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Субтитры для языка '{lang}' не найдены у данного видео."
            )

        # Read raw subtitle content
        try:
            content = found_srt.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка чтения субтитров: {sanitized_err}"
            )

        if format_type.lower() == "txt":
            clean_text = srt_to_clean_txt(content)
            txt_path = job_dir / f"{title}_{lang}.txt"
            txt_path.write_text(clean_text, encoding="utf-8")
            return txt_path, f"{title}_{lang}.txt", "text/plain; charset=utf-8"
        else:  # srt
            out_srt = job_dir / f"{title}_{lang}.srt"
            if found_srt != out_srt:
                found_srt.rename(out_srt)
            return out_srt, f"{title}_{lang}.srt", "text/plain; charset=utf-8"

`

---

### Файл: backend/tests/test_reliability.py

`python
"""
Automated reliability and regression test suite for youtube-analyzer-web.
Covers Render Free 512MB RAM protections:
- Concurrency serialization (MAX_CONCURRENT_DOWNLOADS=1, 503 rejection)
- Height capping and elimination of unconstrained /best and /worst
- Error message credential sanitization (no sensitive data leaks)
- Pre-flight check endpoint (/api/check-download) with video accessibility
- cgroup/RSS memory diagnostics (/api/health)
"""

import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import HTTPException
from starlette.testclient import TestClient

from backend.app.config import settings
from backend.app.limiter import validate_youtube_url
from backend.app.schemas import CheckDownloadResponse, HealthResponse
from backend.app.main import app, get_process_rss_mb
from backend.app.services.cleanup import PROTECTED_FILENAMES
from backend.app.services.youtube import (
    sanitize_error_message,
    _build_format_selector,
    DownloadSlot,
    get_active_downloads_count,
    check_download_feasibility,
)


class TestReliabilityAndSafety(unittest.TestCase):
    """Unit and integration test cases."""

    def setUp(self):
        self.client = TestClient(app)

    # 1. Credentials sanitization tests
    def test_sanitize_error_message_url(self):
        """Ensures proxy credentials in URL formats are cleanly stripped."""
        err = "ProxyError: Cannot connect to http://user_alice:secret_pass_123@10.0.0.1:8080"
        sanitized = sanitize_error_message(err)
        self.assertNotIn("secret_pass_123", sanitized)
        self.assertIn("http://user_alice:***@10.0.0.1:8080", sanitized)

    def test_sanitize_error_message_no_false_positive(self):
        """Ensures normal words sharing substrings with passwords are not ruined."""
        normal_msg = "Video unavailable: This video is private or removed by uploader."
        sanitized = sanitize_error_message(normal_msg)
        self.assertEqual(normal_msg, sanitized)

    # 2. Format selector strict capping tests
    def test_format_selector_720p_capping(self):
        """Ensures 720p selector has NO unconstrained /best and NO unconstrained /worst."""
        selector = _build_format_selector("720p", max_height_cap=720)
        # Every branch must have height <= 720
        parts = selector.split("/")
        for p in parts:
            self.assertTrue(
                "height<=720" in p or "height<=480" in p or "height<=360" in p,
                f"Part {p} violates height cap 720!"
            )
        # Verify no unconstrained 'best' or 'worst' (must be qualified with [height<=...])
        self.assertIsNone(re.search(r'(^|/)best($|/)', selector))
        self.assertIsNone(re.search(r'(^|/)worst($|/)', selector))
        self.assertTrue(selector.endswith("worst[height<=720]"))

    def test_format_selector_360p_capping(self):
        """Ensures 360p selector is strictly bounded to 360 throughout."""
        selector = _build_format_selector("360p", max_height_cap=720)
        parts = selector.split("/")
        for p in parts:
            self.assertTrue("height<=360" in p, f"Part {p} violates height cap 360!")
        self.assertTrue(selector.endswith("worst[height<=360]"))

    def test_format_selector_best_capped(self):
        """Ensures 'best' with server cap 720 is strictly clamped to 720."""
        selector = _build_format_selector("best", max_height_cap=720)
        self.assertIn("height<=720", selector)
        self.assertNotIn("height<=1080", selector)
        self.assertTrue(selector.endswith("worst[height<=720]"))

    def test_format_selector_1080p_when_cap_720(self):
        """Ensures requesting 1080p when server cap is 720 clamps to 720."""
        selector = _build_format_selector("1080p", max_height_cap=720)
        self.assertIn("height<=720", selector)
        self.assertNotIn("height<=1080", selector)

    # 3. Concurrency serialization and 503 rejection
    def test_download_slot_concurrency_serialization(self):
        """Ensures only 1 download can run; second caller receives 503."""
        self.assertEqual(get_active_downloads_count(), 0)
        with DownloadSlot():
            self.assertEqual(get_active_downloads_count(), 1)
            with self.assertRaises(HTTPException) as ctx:
                with DownloadSlot():
                    pass
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("выполняет другую загрузку", ctx.exception.detail)
        self.assertEqual(get_active_downloads_count(), 0)

    # 4. URL Validation tests
    def test_url_validation_video_in_playlist(self):
        """Valid video with &list= parameter must be accepted and normalized."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL12345"
        norm = validate_youtube_url(url)
        self.assertEqual(norm, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_url_validation_playlist_rejection(self):
        """Pure playlist URL must be rejected with 400."""
        url = "https://www.youtube.com/playlist?list=PL12345"
        with self.assertRaises(HTTPException) as ctx:
            validate_youtube_url(url)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("плейлистов целиком", ctx.exception.detail)

    def test_url_validation_channel_rejection(self):
        """Channel URLs must be rejected with 400."""
        for u in ("https://www.youtube.com/@mkbhd", "https://www.youtube.com/channel/UC123"):
            with self.assertRaises(HTTPException) as ctx:
                validate_youtube_url(u)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("каналы не поддерживаются", ctx.exception.detail)

    # 5. Pre-check feasibility with format verification
    @patch("backend.app.services.youtube.get_cached_or_extract_info")
    @patch("backend.app.services.youtube.get_ffmpeg_path")
    def test_check_download_feasibility_ok(self, mock_ffmpeg, mock_info):
        """Pre-check succeeds when video has requested format and FFmpeg exists."""
        mock_ffmpeg.return_value = "ffmpeg"
        mock_info.return_value = {
            "title": "Never Gonna Give You Up",
            "formats": [{"height": 720}, {"height": 480}, {"height": 360}],
        }
        ok, msg, title = check_download_feasibility(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            kind="video",
            quality="720p"
        )
        self.assertTrue(ok)
        self.assertEqual(title, "Never Gonna Give You Up")
        self.assertIn("Never_Gonna_Give_You_Up", msg)

    @patch("backend.app.services.youtube.get_cached_or_extract_info")
    @patch("backend.app.services.youtube.get_ffmpeg_path")
    def test_check_download_feasibility_4k_only_rejection(self, mock_ffmpeg, mock_info):
        """Pre-check rejects video if it only has 4K and requested quality is 720p."""
        mock_ffmpeg.return_value = "ffmpeg"
        mock_info.return_value = {
            "title": "4K Ultra HD Nature",
            "formats": [{"height": 2160}],  # Only 4K available
        }
        ok, msg, title = check_download_feasibility(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            kind="video",
            quality="720p"
        )
        self.assertFalse(ok)
        self.assertIn("Видео недоступно в качестве ≤720p", msg)

    # 6. Cleanup protected filenames
    def test_cleanup_protected_files(self):
        """Ensures cookies.txt, .gitkeep, README.md are strictly protected."""
        self.assertIn("cookies.txt", PROTECTED_FILENAMES)
        self.assertIn(".gitkeep", PROTECTED_FILENAMES)
        self.assertIn("README.md", PROTECTED_FILENAMES)

    # 7. Health endpoint memory diagnostics
    def test_health_endpoint(self):
        """Tests /api/health reports RSS memory and concurrency constraints."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["concurrency_limit"], settings.MAX_CONCURRENT_DOWNLOADS)
        self.assertEqual(data["max_video_height"], settings.MAX_VIDEO_HEIGHT)
        self.assertIn("rss_mb", data)
        self.assertIn("oom_risk", data)
        self.assertIn(data["oom_risk"], ("low", "medium", "high"))

    # 8. Pre-check API endpoint integration
    @patch("backend.app.main.check_download_feasibility")
    def test_check_download_endpoint_success(self, mock_feasibility):
        """Tests GET /api/check-download returns 200 with title."""
        mock_feasibility.return_value = (True, "Готово: test_video", "test_video")
        res = self.client.get(
            "/api/check-download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&kind=video&quality=720p"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["title"], "test_video")


if __name__ == "__main__":
    unittest.main()

`

---

### Файл: docker-compose.yml

`yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: yt-analyzer-web
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - PROXY_URL=${PROXY_URL:-}
      - COOKIES_FILE=${COOKIES_FILE:-}
      - COOKIES_TEXT=${COOKIES_TEXT:-}
      - COOKIES_FROM_BROWSER=${COOKIES_FROM_BROWSER:-}
      - MAX_DURATION_SECONDS=${MAX_DURATION_SECONDS:-14400}
      - MAX_FILE_SIZE_MB=${MAX_FILE_SIZE_MB:-1024}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-30}
    env_file:
      - path: .env
        required: false
    volumes:
      - ./downloads:/app/downloads
      - ./cookies.txt:/app/cookies.txt:ro

`

---

### Файл: Dockerfile

`dockerfile
# Multi-stage/Slim production Dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    HOST=0.0.0.0

# Install system dependencies: ffmpeg for media merging/audio conversion, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user for container security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Install Python requirements first (leveraging Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and static frontend
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create downloads folder and assign ownership to non-root user
RUN mkdir -p /app/downloads && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port (can be overridden by $PORT on Render/Railway/Fly.io)
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch production server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

`

---

### Файл: fly.toml

`toml
app = "yt-analyzer-web"
primary_region = "fra"

[env]
  MAX_CONCURRENT_DOWNLOADS = "1"
  MAX_VIDEO_HEIGHT = "720"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[http_service.checks]]
  grace_period = "10s"
  interval = "30s"
  method = "GET"
  timeout = "5s"
  path = "/api/health"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"

`

---

### Файл: frontend/app.js

`javascript
/**
 * YouTube Video Analyzer & Downloader Frontend Controller
 */

// Application state
let currentVideoData = null;
let currentTranscriptText = "";

// DOM Elements
const serverStatusDot = document.getElementById("serverStatusDot");
const serverStatusText = document.getElementById("serverStatusText");

const analyzeForm = document.getElementById("analyzeForm");
const urlInput = document.getElementById("urlInput");
const pasteBtn = document.getElementById("pasteBtn");
const clearBtn = document.getElementById("clearBtn");
const submitBtn = document.getElementById("submitBtn");
const submitSpinner = document.getElementById("submitSpinner");

const alertBox = document.getElementById("alertBox");
const alertTitle = document.getElementById("alertTitle");
const alertDesc = document.getElementById("alertDesc");
const alertCloseBtn = document.getElementById("alertCloseBtn");

const skeletonLoader = document.getElementById("skeletonLoader");
const resultSection = document.getElementById("resultSection");

// Result card elements
const videoThumb = document.getElementById("videoThumb");
const videoDuration = document.getElementById("videoDuration");
const videoTitle = document.getElementById("videoTitle");
const channelLink = document.getElementById("channelLink");
const channelName = document.getElementById("channelName");
const uploadDate = document.getElementById("uploadDate");
const viewCount = document.getElementById("viewCount");
const originalVideoLink = document.getElementById("originalVideoLink");
const copyUrlBtn = document.getElementById("copyUrlBtn");
const videoDescription = document.getElementById("videoDescription");

// Grids & tabs
const videoOptionsGrid = document.getElementById("videoOptionsGrid");
const audioOptionsGrid = document.getElementById("audioOptionsGrid");
const subtitlesContent = document.getElementById("subtitlesContent");
const formatsTableBody = document.getElementById("formatsTableBody");

// Modal elements
const transcriptModal = document.getElementById("transcriptModal");
const modalBackdrop = document.getElementById("modalBackdrop");
const modalCloseBtn = document.getElementById("modalCloseBtn");
const modalTitle = document.getElementById("modalTitle");
const modalText = document.getElementById("modalText");
const modalLoading = document.getElementById("modalLoading");
const modalCopyBtn = document.getElementById("modalCopyBtn");
const modalDownloadBtn = document.getElementById("modalDownloadBtn");

// Toast
const toast = document.getElementById("toast");

/* -------------------------------------------------------------
 * 1. Health check & Initializer
 * ------------------------------------------------------------- */
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    serverStatusDot.className = "status-indicator online";
    let statusMsg = "Сервер онлайн";
    if (data.ffmpeg_available) statusMsg += " (FFmpeg)";
    if (data.cookies_configured) statusMsg += " • Cookies";
    if (data.proxy_configured) statusMsg += " • Прокси";
    if (data.rss_mb > 0) statusMsg += ` • RAM: ${data.rss_mb} МБ`;
    serverStatusText.textContent = statusMsg;
  } catch (err) {
    serverStatusDot.className = "status-indicator offline";
    serverStatusText.textContent = "Сервер недоступен";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  setupEventListeners();
});

/* -------------------------------------------------------------
 * 2. Event Listeners Setup
 * ------------------------------------------------------------- */
function setupEventListeners() {
  // Input clear / paste handlers
  urlInput.addEventListener("input", () => {
    if (urlInput.value.trim().length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    urlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        clearBtn.classList.remove("hidden");
        urlInput.focus();
      }
    } catch (e) {
      showToast("Не удалось прочитать буфер обмена");
    }
  });

  // Sample chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const url = chip.getAttribute("data-url");
      urlInput.value = url;
      clearBtn.classList.remove("hidden");
      analyzeForm.dispatchEvent(new Event("submit"));
    });
  });

  // Form submit
  analyzeForm.addEventListener("submit", handleAnalyzeSubmit);

  // Alert close
  alertCloseBtn.addEventListener("click", hideAlert);

  // Copy video URL
  copyUrlBtn.addEventListener("click", () => {
    if (currentVideoData && currentVideoData.original_url) {
      navigator.clipboard.writeText(currentVideoData.original_url);
      showToast("Ссылка скопирована в буфер обмена!");
    }
  });

  // Tabs switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    });
  });

  // Modal actions
  modalCloseBtn.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  modalCopyBtn.addEventListener("click", () => {
    if (currentTranscriptText) {
      navigator.clipboard.writeText(currentTranscriptText);
      showToast("Текст расшифровки скопирован!");
    }
  });
}

/* -------------------------------------------------------------
 * 3. Video Analysis API
 * ------------------------------------------------------------- */
async function handleAnalyzeSubmit(e) {
  e.preventDefault();
  const rawUrl = urlInput.value.trim();
  if (!rawUrl) return;

  hideAlert();
  setLoading(true);
  resultSection.classList.add("hidden");
  skeletonLoader.classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Произошла ошибка при анализе видео.");
    }

    currentVideoData = data;
    renderResults(data);
    resultSection.classList.remove("hidden");
  } catch (err) {
    showAlert("Ошибка анализа", err.message);
  } finally {
    setLoading(false);
    skeletonLoader.classList.add("hidden");
  }
}

/* -------------------------------------------------------------
 * 4. Render Results View
 * ------------------------------------------------------------- */
function renderResults(data) {
  // Video thumbnail & duration
  videoThumb.src = data.thumbnail || "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>";
  videoThumb.alt = data.title;
  videoDuration.textContent = data.duration_str;

  // Title & Channel
  videoTitle.textContent = data.title;
  channelName.textContent = data.channel;
  if (data.channel_url) {
    channelLink.href = data.channel_url;
    channelLink.style.display = "inline-flex";
  } else {
    channelLink.style.display = "none";
  }

  // Publish date & views
  uploadDate.textContent = data.upload_date ? `Опубликовано: ${data.upload_date}` : "Дата неизвестна";
  viewCount.textContent = data.view_count ? `${data.view_count.toLocaleString("ru-RU")} просмотров` : "— просмотров";

  // Original Link
  originalVideoLink.href = data.original_url;

  // Description
  videoDescription.textContent = data.description || "Описание отсутствует.";

  // 1. Render Video Options
  renderVideoOptions(data.video_options, data.original_url);

  // 2. Render Audio Options
  renderAudioOptions(data.audio_options, data.original_url);

  // 3. Render Subtitles Options
  renderSubtitlesOptions(data.subtitle_options, data.original_url);

  // 4. Render Raw Formats Table
  renderRawFormatsTable(data.all_formats);
}

function renderVideoOptions(options, url) {
  videoOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    videoOptionsGrid.innerHTML = `<p class="empty-msg">Варианты видео не найдены.</p>`;
    return;
  }

  options.forEach((opt) => {
    const card = document.createElement("div");
    card.className = "download-card";
    card.innerHTML = `
      <div class="download-card-header">
        <span class="card-quality-badge">${escapeHtml(opt.quality.toUpperCase())}</span>
        <span class="card-format-tag">${escapeHtml(opt.ext)}</span>
      </div>
      <div class="card-details">
        <span>${escapeHtml(opt.label)}</span>
        <span class="card-size">${escapeHtml(opt.filesize_str)}</span>
      </div>
      <button type="button" class="download-action-btn" data-url="${escapeHtml(opt.download_url)}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span>Скачать видео</span>
      </button>
    `;

    const btn = card.querySelector(".download-action-btn");
    btn.addEventListener("click", () => triggerDownload(btn, opt.download_url));

    videoOptionsGrid.appendChild(card);
  });
}

function renderAudioOptions(options, url) {
  audioOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    audioOptionsGrid.innerHTML = `<p class="empty-msg">Варианты аудио не найдены.</p>`;
    return;
  }

  options.forEach((opt) => {
    const card = document.createElement("div");
    card.className = "download-card";
    card.innerHTML = `
      <div class="download-card-header">
        <span class="card-quality-badge">${escapeHtml(opt.format.toUpperCase())}</span>
        <span class="card-format-tag">${opt.bitrate_kbps} kbps</span>
      </div>
      <div class="card-details">
        <span>${escapeHtml(opt.label)}</span>
        <span class="card-size">${escapeHtml(opt.filesize_str)}</span>
      </div>
      <button type="button" class="download-action-btn" data-url="${escapeHtml(opt.download_url)}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span>Скачать ${opt.format.toUpperCase()}</span>
      </button>
    `;

    const btn = card.querySelector(".download-action-btn");
    btn.addEventListener("click", () => triggerDownload(btn, opt.download_url));

    audioOptionsGrid.appendChild(card);
  });
}

function renderSubtitlesOptions(options, url) {
  if (!options || options.length === 0) {
    subtitlesContent.innerHTML = `
      <div class="subtitles-layout">
        <p class="empty-msg" style="color: var(--text-muted); padding: 12px 0;">
          ⚠️ Субтитры или автоматические расшифровки для этого видео отсутствуют на YouTube.
        </p>
      </div>
    `;
    return;
  }

  let selectOptions = options
    .map((sub, idx) => `<option value="${idx}">${escapeHtml(sub.name)} (${sub.lang})</option>`)
    .join("");

  subtitlesContent.innerHTML = `
    <div class="subtitles-layout">
      <div class="subtitles-controls">
        <div class="form-group" style="flex: 1; min-width: 220px;">
          <label class="form-label" for="subLangSelect">Языковая дорожка</label>
          <select id="subLangSelect" class="select-control">
            ${selectOptions}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Формат файла</label>
          <div class="format-radios">
            <label class="radio-chip">
              <input type="radio" name="subFormat" value="txt" checked>
              <span>Чистый текст (.txt)</span>
            </label>
            <label class="radio-chip">
              <input type="radio" name="subFormat" value="srt">
              <span>Субтитры с таймкодами (.srt)</span>
            </label>
          </div>
        </div>
      </div>

      <div class="subtitles-actions">
        <button type="button" id="downloadSubBtn" class="btn btn-primary">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Скачать файл
        </button>
        <button type="button" id="previewSubBtn" class="btn btn-secondary">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          Быстрый просмотр текста
        </button>
      </div>
    </div>
  `;

  const subSelect = document.getElementById("subLangSelect");
  const downloadSubBtn = document.getElementById("downloadSubBtn");
  const previewSubBtn = document.getElementById("previewSubBtn");

  downloadSubBtn.addEventListener("click", () => {
    const selectedIdx = parseInt(subSelect.value, 10);
    const sub = options[selectedIdx];
    const fmt = document.querySelector('input[name="subFormat"]:checked').value;
    const downloadUrl = fmt === "txt" ? sub.txt_url : sub.srt_url;
    triggerDownload(downloadSubBtn, downloadUrl);
  });

  previewSubBtn.addEventListener("click", () => {
    const selectedIdx = parseInt(subSelect.value, 10);
    const sub = options[selectedIdx];
    openTranscriptModal(sub);
  });
}

function renderRawFormatsTable(formats) {
  formatsTableBody.innerHTML = "";
  if (!formats || formats.length === 0) {
    formatsTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Форматы не найдены</td></tr>`;
    return;
  }

  formats.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${escapeHtml(f.format_id)}</code></td>
      <td><strong>${escapeHtml(f.ext)}</strong></td>
      <td>${escapeHtml(f.resolution)}</td>
      <td>${f.fps ? f.fps : "—"}</td>
      <td>${escapeHtml(f.filesize_str)}</td>
      <td><code>${escapeHtml(f.vcodec || "none")}</code></td>
      <td><code>${escapeHtml(f.acodec || "none")}</code></td>
      <td>${escapeHtml(f.note || "—")}</td>
    `;
    formatsTableBody.appendChild(tr);
  });
}

/* -------------------------------------------------------------
 * 5. Download Streaming Handler
 * ------------------------------------------------------------- */
async function triggerDownload(btn, url) {
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <div class="spinner" style="width:14px;height:14px;"></div>
    <span>Проверка...</span>
  `;

  try {
    // 1. Parse target download URL parameters for pre-flight check
    const urlObj = new URL(url, window.location.origin);
    const ytUrl = urlObj.searchParams.get("url");
    let kind = "video";
    if (url.includes("/api/download/audio")) kind = "audio";
    else if (url.includes("/api/download/transcript")) kind = "transcript";

    const checkParams = new URLSearchParams({ url: ytUrl, kind });
    const quality = urlObj.searchParams.get("quality");
    const format = urlObj.searchParams.get("format");
    const lang = urlObj.searchParams.get("lang");
    if (quality) checkParams.set("quality", quality);
    if (format) checkParams.set("format", format);
    if (lang) checkParams.set("lang", lang);

    // 2. Perform pre-check on backend (concurrency, limits, ffmpeg, video availability)
    const checkRes = await fetch("/api/check-download?" + checkParams.toString());
    if (!checkRes.ok) {
      let errorDetail = "Ошибка при проверке возможности скачивания";
      try {
        const errJson = await checkRes.json();
        errorDetail = errJson.detail || errorDetail;
      } catch (e) {
        errorDetail = `Ошибка сервера (${checkRes.status})`;
      }
      showAlert("Невозможно начать скачивание", errorDetail);
      return;
    }

    let downloadFilename = "download";
    try {
      const checkData = await checkRes.json();
      if (checkData.title) {
        const ext = kind === "audio" ? (format || "mp3") : (kind === "transcript" ? (lang ? `${lang}.${format || "txt"}` : (format || "txt")) : "mp4");
        downloadFilename = `${checkData.title}.${ext}`;
      }
    } catch (e) {
      // ignore JSON parse if empty
    }

    // 3. Pre-check succeeded: trigger native direct streaming download via <a> tag.
    // Avoids buffering multi-hundred MB into browser V8 JS heap (prevents browser tab OOM crashes).
    showToast("Сервер готовит поток. Файл сохраняется напрямую браузером...");
    const a = document.createElement("a");
    a.href = url;
    a.setAttribute("download", downloadFilename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (err) {
    showAlert("Ошибка сети", `Не удалось выполнить проверку или начать загрузку: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/* -------------------------------------------------------------
 * 6. Transcript Preview Modal
 * ------------------------------------------------------------- */
async function openTranscriptModal(subOption) {
  transcriptModal.classList.remove("hidden");
  modalTitle.textContent = `Транскрипт: ${subOption.name}`;
  modalText.textContent = "";
  modalLoading.classList.remove("hidden");
  currentTranscriptText = "";

  try {
    const res = await fetch(subOption.txt_url);
    if (!res.ok) throw new Error("Не удалось загрузить текст субтитров");
    const text = await res.text();
    currentTranscriptText = text;
    modalText.textContent = text || "(Субтитры пусты)";
  } catch (err) {
    modalText.textContent = `Ошибка: ${err.message}`;
  } finally {
    modalLoading.classList.add("hidden");
  }

  modalDownloadBtn.onclick = () => {
    triggerDownload(modalDownloadBtn, subOption.txt_url);
  };
}

function closeModal() {
  transcriptModal.classList.add("hidden");
}

/* -------------------------------------------------------------
 * 7. Helpers & UI Feedback
 * ------------------------------------------------------------- */
function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  urlInput.disabled = isLoading;
  const btnText = submitBtn.querySelector(".btn-text");
  if (isLoading) {
    btnText.textContent = "Анализирую...";
    submitSpinner.classList.remove("hidden");
  } else {
    btnText.textContent = "Анализировать";
    submitSpinner.classList.add("hidden");
  }
}

function showAlert(title, desc) {
  alertTitle.textContent = title;
  alertDesc.textContent = desc;
  alertBox.classList.remove("hidden");
  alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideAlert() {
  alertBox.classList.add("hidden");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

`

---

### Файл: frontend/index.html

`html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube Analyzer & Downloader</title>
  <meta name="description" content="Анализ видео YouTube, скачивание видео в высоком качестве, извлечение чистого аудио MP3/M4A и текстового транскрипта без таймкодов.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>▶️</text></svg>">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <!-- Header -->
  <header class="header">
    <div class="container header-inner">
      <div class="brand">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="4" width="20" height="16" rx="4" fill="#ff0033" stroke="none"/>
            <polygon points="10,8 16,12 10,16" fill="#ffffff" stroke="none"/>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">YouTube <span>Analyzer</span></span>
          <span class="brand-tag">Web Edition</span>
        </div>
      </div>
      <div class="header-status">
        <span class="status-indicator" id="serverStatusDot"></span>
        <span class="status-text" id="serverStatusText">Проверка сервера...</span>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="main-content">
    <div class="container">
      
      <!-- Hero Section -->
      <section class="hero-section">
        <h1 class="hero-title">Анализ и скачивание видео <span class="gradient-text">YouTube</span></h1>
        <p class="hero-subtitle">
          Получайте подробные метаданные, скачивайте видео в любом качестве (до 1080p/Best),
          извлекайте аудио (MP3/M4A) и чистый текст субтитров без лишних таймкодов.
        </p>

        <!-- Search Bar -->
        <form id="analyzeForm" class="search-form">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input 
              type="text" 
              id="urlInput" 
              class="url-input" 
              placeholder="Вставьте ссылку на YouTube (например: https://www.youtube.com/watch?v=...)" 
              required
              autocomplete="off"
            >
            <button type="button" id="pasteBtn" class="action-icon-btn" title="Вставить из буфера">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
              </svg>
            </button>
            <button type="button" id="clearBtn" class="action-icon-btn hidden" title="Очистить">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            <button type="submit" id="submitBtn" class="submit-btn">
              <span class="btn-text">Анализировать</span>
              <div class="spinner hidden" id="submitSpinner"></div>
            </button>
          </div>
        </form>

        <!-- Sample URLs -->
        <div class="sample-chips">
          <span class="chips-label">Быстрый тест:</span>
          <button type="button" class="chip-btn" data-url="https://www.youtube.com/watch?v=jNQXAC9IVRw">Первое видео YouTube (19s)</button>
          <button type="button" class="chip-btn" data-url="https://www.youtube.com/watch?v=dQw4w9WgXcQ">Rick Astley</button>
        </div>
      </section>

      <!-- Alert Box -->
      <div id="alertBox" class="alert-box hidden">
        <div class="alert-icon" id="alertIcon">⚠️</div>
        <div class="alert-content">
          <div class="alert-title" id="alertTitle">Ошибка</div>
          <div class="alert-desc" id="alertDesc">Текст ошибки</div>
        </div>
        <button type="button" class="alert-close" id="alertCloseBtn">&times;</button>
      </div>

      <!-- Loading Skeleton -->
      <div id="skeletonLoader" class="skeleton-wrapper hidden">
        <div class="skeleton skeleton-header"></div>
        <div class="skeleton-body">
          <div class="skeleton skeleton-thumb"></div>
          <div class="skeleton-details">
            <div class="skeleton skeleton-line line-title"></div>
            <div class="skeleton skeleton-line line-meta"></div>
            <div class="skeleton skeleton-line line-meta"></div>
            <div class="skeleton skeleton-line line-btn"></div>
          </div>
        </div>
      </div>

      <!-- Result Card -->
      <section id="resultSection" class="result-section hidden">
        <!-- Overview Card -->
        <div class="video-card">
          <div class="video-thumb-container">
            <img id="videoThumb" src="" alt="Превью видео" class="video-thumb">
            <span class="duration-badge" id="videoDuration">00:00</span>
          </div>

          <div class="video-info">
            <h2 id="videoTitle" class="video-title">Название видео</h2>
            
            <div class="meta-row">
              <a id="channelLink" href="#" target="_blank" rel="noopener noreferrer" class="meta-item channel-item">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span id="channelName">Канал</span>
              </a>

              <div class="meta-item">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                <span id="uploadDate">Дата публикации</span>
              </div>

              <div class="meta-item">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                <span id="viewCount">0 просмотров</span>
              </div>
            </div>

            <div class="video-actions">
              <a id="originalVideoLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                </svg>
                Открыть оригинал
              </a>
              <button type="button" id="copyUrlBtn" class="btn btn-secondary">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                Копировать ссылку
              </button>
            </div>

            <!-- Description toggle -->
            <details class="description-accordion" id="descAccordion">
              <summary class="desc-summary">Описание видео</summary>
              <div class="desc-body" id="videoDescription">Нет описания.</div>
            </details>
          </div>
        </div>

        <!-- Download Tabs -->
        <div class="tabs-container">
          <div class="tabs-nav" role="tablist">
            <button type="button" class="tab-btn active" data-tab="tab-video" role="tab">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                <line x1="7" y1="2" x2="7" y2="22"></line>
                <line x1="17" y1="2" x2="17" y2="22"></line>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <line x1="2" y1="7" x2="7" y2="7"></line>
                <line x1="2" y1="17" x2="7" y2="17"></line>
                <line x1="17" y1="17" x2="22" y2="17"></line>
                <line x1="17" y1="7" x2="22" y2="7"></line>
              </svg>
              Видео (MP4)
            </button>
            <button type="button" class="tab-btn" data-tab="tab-audio" role="tab">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
              </svg>
              Аудио (MP3 / M4A)
            </button>
            <button type="button" class="tab-btn" data-tab="tab-subtitles" role="tab">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              Транскрипт / Субтитры
            </button>
            <button type="button" class="tab-btn" data-tab="tab-raw" role="tab">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 7 4 4 20 4 20 7"></polyline>
                <line x1="9" y1="20" x2="15" y2="20"></line>
                <line x1="12" y1="4" x2="12" y2="20"></line>
              </svg>
              Все форматы yt-dlp
            </button>
          </div>

          <!-- Video Panel -->
          <div class="tab-panel active" id="tab-video" role="tabpanel">
            <div class="panel-header">
              <h3 class="panel-title">Варианты скачивания видео (MP4)</h3>
              <p class="panel-subtitle">Сервер автоматически объединяет видеопоток с наилучшим аудиопотоком через FFmpeg.</p>
            </div>
            <div class="download-grid" id="videoOptionsGrid">
              <!-- Rendered via JS -->
            </div>
          </div>

          <!-- Audio Panel -->
          <div class="tab-panel" id="tab-audio" role="tabpanel">
            <div class="panel-header">
              <h3 class="panel-title">Варианты скачивания аудио</h3>
              <p class="panel-subtitle">MP3 конвертируется в 320 kbps через FFmpeg, M4A скачивается в оригинальном AAC-контейнере.</p>
            </div>
            <div class="download-grid" id="audioOptionsGrid">
              <!-- Rendered via JS -->
            </div>
          </div>

          <!-- Subtitles Panel -->
          <div class="tab-panel" id="tab-subtitles" role="tabpanel">
            <div class="panel-header">
              <h3 class="panel-title">Расшифровка и субтитры</h3>
              <p class="panel-subtitle">Чистый текст (.txt) очищен от дубликатов строк и таймкодов (алгоритм из analyze.py), а .srt подходит для медиаплееров.</p>
            </div>
            <div id="subtitlesContent">
              <!-- Rendered via JS -->
            </div>
          </div>

          <!-- Raw Formats Panel -->
          <div class="tab-panel" id="tab-raw" role="tabpanel">
            <div class="panel-header">
              <h3 class="panel-title">Техническая таблица всех стримов</h3>
              <p class="panel-subtitle">Полный перечень потоков, доступных для этого видео через движок yt-dlp.</p>
            </div>
            <div class="table-responsive">
              <table class="formats-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Расширение</th>
                    <th>Разрешение</th>
                    <th>FPS</th>
                    <th>Размер</th>
                    <th>Видеокодек</th>
                    <th>Аудиокодек</th>
                    <th>Инфо</th>
                  </tr>
                </thead>
                <tbody id="formatsTableBody">
                  <!-- Rendered via JS -->
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

    </div>
  </main>

  <!-- Transcript Preview Modal -->
  <div id="transcriptModal" class="modal hidden">
    <div class="modal-backdrop" id="modalBackdrop"></div>
    <div class="modal-card">
      <div class="modal-header">
        <h3 class="modal-title" id="modalTitle">Просмотр расшифровки</h3>
        <button type="button" class="modal-close" id="modalCloseBtn">&times;</button>
      </div>
      <div class="modal-body">
        <div class="modal-loading hidden" id="modalLoading">
          <div class="spinner"></div>
          <span>Загрузка текста...</span>
        </div>
        <pre class="transcript-pre" id="modalText"></pre>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" id="modalCopyBtn">Скопировать весь текст</button>
        <button type="button" class="btn btn-primary" id="modalDownloadBtn">Скачать .txt</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="toast hidden">Сообщение</div>

  <!-- Footer -->
  <footer class="footer">
    <div class="container footer-inner">
      <p class="footer-copy">© 2026 YouTube Video Analyzer & Downloader. Лицензия MIT.</p>
      <div class="footer-links">
        <span>FastAPI</span>
        <span>•</span>
        <span>yt-dlp</span>
        <span>•</span>
        <span>FFmpeg</span>
      </div>
    </div>
  </footer>

  <script src="app.js"></script>
</body>
</html>

`

---

### Файл: frontend/style.css

`css
/* Global CSS & Reset */
:root {
  --bg-color: #0b0f19;
  --bg-card: #131b2e;
  --bg-card-hover: #1a243d;
  --bg-input: #1b243b;
  --border-color: #263353;
  --border-focus: #ff0033;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-dim: #64748b;
  --accent-red: #ff0033;
  --accent-red-hover: #e6002e;
  --accent-blue: #3b82f6;
  --accent-green: #10b981;
  --accent-amber: #f59e0b;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.35);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
  --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-family);
  background-color: var(--bg-color);
  color: var(--text-main);
  line-height: 1.5;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.container {
  width: 100%;
  max-width: 1140px;
  margin: 0 auto;
  padding: 0 1.25rem;
}

/* Header */
.header {
  border-bottom: 1px solid var(--border-color);
  background: rgba(11, 15, 25, 0.85);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-name span {
  color: var(--accent-red);
}

.brand-tag {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  background: var(--bg-card);
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent-amber);
  display: inline-block;
  box-shadow: 0 0 8px currentColor;
}

.status-indicator.online {
  background-color: var(--accent-green);
  color: var(--accent-green);
}

.status-indicator.offline {
  background-color: var(--accent-red);
  color: var(--accent-red);
}

/* Main Content */
.main-content {
  flex: 1;
  padding: 2.5rem 0;
}

/* Hero Section */
.hero-section {
  text-align: center;
  margin-bottom: 2.5rem;
}

.hero-title {
  font-size: 2.4rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0.75rem;
}

.gradient-text {
  background: linear-gradient(135deg, #ff0033 0%, #ff6b81 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 1.05rem;
  color: var(--text-muted);
  max-width: 680px;
  margin: 0 auto 2rem auto;
}

/* Search Form */
.search-form {
  max-width: 800px;
  margin: 0 auto 1.25rem auto;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 6px 8px 6px 16px;
  box-shadow: var(--shadow-md);
  transition: all 0.2s ease;
}

.search-box:focus-within {
  border-color: var(--accent-red);
  box-shadow: 0 0 0 3px rgba(255, 0, 51, 0.2), var(--shadow-lg);
}

.search-icon {
  color: var(--text-dim);
  flex-shrink: 0;
  margin-right: 12px;
}

.url-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-main);
  font-size: 1rem;
  font-family: inherit;
  min-width: 0;
}

.url-input::placeholder {
  color: var(--text-dim);
}

.action-icon-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.action-icon-btn:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.08);
}

.submit-btn {
  background: var(--accent-red);
  color: white;
  border: none;
  outline: none;
  font-weight: 600;
  font-size: 0.95rem;
  padding: 10px 22px;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
  margin-left: 6px;
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-red-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 0, 51, 0.35);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Sample chips */
.sample-chips {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chips-label {
  font-size: 0.85rem;
  color: var(--text-dim);
}

.chip-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.8rem;
  padding: 4px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-main);
  border-color: var(--accent-red);
}

/* Alert Box */
.alert-box {
  max-width: 800px;
  margin: 0 auto 2rem auto;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.alert-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: #fca5a5;
  margin-bottom: 2px;
}

.alert-desc {
  font-size: 0.875rem;
  color: #f87171;
  word-break: break-word;
}

.alert-close {
  background: transparent;
  border: none;
  color: #fca5a5;
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
}

/* Skeleton loader */
.skeleton-wrapper {
  max-width: 1000px;
  margin: 0 auto;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.skeleton {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-body {
  display: flex;
  gap: 20px;
  margin-top: 16px;
}

.skeleton-thumb {
  width: 320px;
  height: 180px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

.skeleton-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 18px;
}

.line-title { width: 85%; height: 26px; }
.line-meta { width: 45%; }
.line-btn { width: 140px; height: 38px; margin-top: auto; }

/* Result Section */
.result-section {
  max-width: 1000px;
  margin: 0 auto;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Video Card */
.video-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  gap: 24px;
  box-shadow: var(--shadow-md);
  margin-bottom: 2rem;
}

.video-thumb-container {
  position: relative;
  width: 340px;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #000;
  flex-shrink: 0;
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.video-thumb-container:hover .video-thumb {
  transform: scale(1.03);
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  backdrop-filter: blur(4px);
}

.video-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.video-title {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 12px;
  color: var(--text-main);
  word-break: break-word;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.channel-item {
  color: #60a5fa;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.15s ease;
}

.channel-item:hover {
  color: #93c5fd;
  text-decoration: underline;
}

.video-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  border: none;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: #475569;
}

.btn-primary {
  background: var(--accent-red);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-red-hover);
}

.description-accordion {
  margin-top: auto;
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}

.desc-summary {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-dim);
  cursor: pointer;
  user-select: none;
}

.desc-summary:hover {
  color: var(--text-muted);
}

.desc-body {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* Tabs */
.tabs-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.tabs-nav {
  display: flex;
  background: rgba(11, 15, 25, 0.6);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.03);
}

.tab-btn.active {
  color: var(--text-main);
  border-bottom-color: var(--accent-red);
  background: rgba(255, 0, 51, 0.06);
}

.tab-panel {
  display: none;
  padding: 24px;
}

.tab-panel.active {
  display: block;
  animation: fadeIn 0.2s ease;
}

.panel-header {
  margin-bottom: 20px;
}

.panel-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.panel-subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* Download Grid */
.download-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.download-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.download-card:hover {
  border-color: #475569;
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.download-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-quality-badge {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main);
}

.card-format-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.card-details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.card-size {
  font-weight: 600;
  color: var(--accent-green);
  background: rgba(16, 185, 129, 0.12);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.download-action-btn {
  width: 100%;
  padding: 10px;
  background: var(--accent-red);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.download-action-btn:hover:not(:disabled) {
  background: var(--accent-red-hover);
}

.download-action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Subtitles tab layout */
.subtitles-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.subtitles-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  background: var(--bg-input);
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}

.select-control {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  outline: none;
}

.format-radios {
  display: flex;
  gap: 10px;
}

.radio-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.85rem;
  user-select: none;
}

.radio-chip input {
  accent-color: var(--accent-red);
}

.subtitles-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* Raw Table */
.table-responsive {
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.formats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  text-align: left;
}

.formats-table th {
  background: rgba(11, 15, 25, 0.7);
  padding: 10px 14px;
  color: var(--text-muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.formats-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--text-main);
}

.formats-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

/* Modal */
.modal {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
}

.modal-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 720px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  z-index: 10;
  animation: fadeIn 0.2s ease;
}

.modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: 1.15rem;
  font-weight: 700;
}

.modal-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.6rem;
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.transcript-pre {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-main);
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  color: var(--text-muted);
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #1e293b;
  border: 1px solid #475569;
  color: white;
  padding: 12px 20px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  font-size: 0.9rem;
  font-weight: 500;
  z-index: 150;
  animation: slideUp 0.25s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Spinner */
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Footer */
.footer {
  border-top: 1px solid var(--border-color);
  background: var(--bg-card);
  padding: 20px 0;
  margin-top: auto;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.85rem;
  color: var(--text-dim);
}

.footer-links {
  display: flex;
  gap: 8px;
  color: var(--text-muted);
}

.hidden {
  display: none !important;
}

/* Responsive */
@media (max-width: 820px) {
  .hero-title { font-size: 1.85rem; }
  .video-card { flex-direction: column; }
  .video-thumb-container { width: 100%; }
}

`

---

### Файл: LICENSE

`text
MIT License

Copyright (c) 2026 YouTube Analyzer Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

`

---

### Файл: package.json

`json
{
  "name": "youtube-analyzer-web",
  "version": "1.0.0",
  "description": "Full-stack YouTube video metadata analyzer, media downloader and transcript extractor",
  "main": "backend/app/main.py",
  "scripts": {
    "start": "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000",
    "dev": "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload",
    "docker:build": "docker build -t yt-analyzer-web .",
    "docker:run": "docker run -p 8000:8000 --env-file .env yt-analyzer-web",
    "compose:up": "docker compose up -d",
    "compose:down": "docker compose down"
  },
  "keywords": [
    "youtube",
    "yt-dlp",
    "fastapi",
    "video-downloader",
    "transcript",
    "subtitles",
    "ffmpeg"
  ],
  "author": "YouTube Analyzer Contributors",
  "license": "MIT"
}

`

---

### Файл: README.md

`markdown
# YouTube Video Analyzer & Downloader 🚀

Полнофункциональный веб-сервис для анализа метаданных видеороликов с YouTube, скачивания видео в высоком качестве (до 1080p / Best), извлечения чистого аудио (MP3 320 kbps / M4A) и экспорта расшифровки субтитров (чистый текст `.txt` без таймкодов и дублей или `.srt` для плееров).

Создан на базе логики скрипта `analyze.py` с переходом на современный асинхронный веб-стек.

---

## 🌟 Возможности сервиса

1. **Анализ метаданных в 1 клик**:
   - Название видео, канал/автор (со ссылкой на канал), длительность, точная дата публикации, количество просмотров.
   - Полноразмерное превью (thumbnail) с таймкодом и прямая ссылка на оригинал на YouTube.
   - Сворачиваемый блок с полным описанием видео.
2. **Скачивание видео (MP4)**:
   - Выбор качества: `1080p (Full HD)`, `720p (HD)`, `480p (SD)`, `360p`, `Best (Original)`.
   - Автоматическое объединение видеопотока и наилучшего аудиопотока через **FFmpeg**.
   - Отображение примерного размера файла (в МБ/ГБ) рядом с каждым вариантом.
3. **Скачивание аудио (MP3 / M4A)**:
   - **MP3**: конвертация аудиодорожки с битрейтом 320 kbps через FFmpeg.
   - **M4A**: прямое скачивание оригинального AAC-потока YouTube без потери качества и перекодирования.
4. **Транскрипт и субтитры**:
   - Автоматический поиск ручных и автоматически сгенерированных субтитров на разных языках (`ru`, `en` и др.).
   - **Чистый текст (`.txt`)**: фильтрация таймкодов, служебных тегов и дедупликация строк (проверенный алгоритм из `analyze.py`).
   - **Файл субтитров (`.srt`)**: стандартный формат с таймкодами.
   - Встроенное модальное окно для быстрого предпросмотра и копирования текста в буфер обмена без скачивания.
5. **Технический инспектор форматов**:
   - Таблица всех доступных стримов `yt-dlp` (`format_id`, разрешение, FPS, кодеки, примерный размер).
6. **Реальный стриминг и автоматическая очистка**:
   - Сервер стримит файл пользователю с корректным заголовком `Content-Disposition` (поддерживаются русские названия).
   - Временные файлы автоматически удаляются сразу после завершения отдачи клиенту (`BackgroundTasks`) + периодический фоновый сборщик мусора (защита диска от переполнения).

---

## 🏗 Архитектура и обоснование стека

```
youtube-analyzer-web/
├── backend/                  # Серверная часть (FastAPI + yt-dlp + FFmpeg)
│   └── app/
│       ├── __init__.py
│       ├── config.py         # Настройки и чтение переменных окружения (.env)
│       ├── limiter.py        # Rate-limiter (IP) и валидация URL (защита от SSRF)
│       ├── main.py           # Точки входа API, стриминг файлов и раздача статики
│       ├── schemas.py        # Pydantic-схемы валидации запросов и ответов
│       └── services/
│           ├── __init__.py
│           ├── cleanup.py    # Автоматическая очистка временных скачанных файлов
│           └── youtube.py    # Логика yt-dlp: метаданные, субтитры, слияние аудио/видео
├── frontend/                 # Клиентская часть (Modern Vanilla SPA)
│   ├── index.html            # Семантическая разметка, доступность, превью, модальные окна
│   ├── style.css             # Тёмная тема, адаптивная сетка, скелетоны, анимации
│   └── app.js                # Контроллер: Fetch API, скачивание файлов, реактивный UI
├── .env.example              # Образец конфигурационных переменных
├── .gitignore                # Исключение кэшей, venv, временных файлов и секретов
├── Dockerfile                # Оптимизированный образ на базе python:3.11-slim с ffmpeg
├── docker-compose.yml        # Готовый запуск одной командой
├── fly.toml                  # Конфигурация для деплоя на Fly.io
├── LICENSE                   # Лицензия MIT
├── package.json              # Вспомогательные скрипты запуска для npm
├── README.md                 # Документация и инструкции по деплою
├── render.yaml               # Конфигурация деплоя для Render Blueprint
└── requirements.txt          # Python-зависимости с зафиксированными версиями
```

### Почему чистый HTML5/CSS3/ES6 SPA вместо тяжелых фреймворков (React/Vite)?
1. **Zero-Build & Легковесность**: Нет этапа сборки (`npm run build`), нет гигабайтной папки `node_modules`. Docker-образ собирается за 30 секунд и весит менее 180 МБ.
2. **Единый сервис**: Бэкенд FastAPI напрямую раздаёт статику (`StaticFiles(directory="frontend", html=True)`). Это позволяет развернуть весь сайт на **одном бесплатном инстансе** без необходимости настраивать CORS и поддерживать два разных хостинга.
3. **Мгновенный старт (0ms Hydration)**: Нативные браузерные возможности (Streams, Blob, Fetch, Clipboard API).

---

## 🔒 Безопасность и ограничения

1. **SSRF-защита**: Разрешены исключительно домены `youtube.com`, `m.youtube.com`, `youtu.be`. Любые обращения к внутренним IP (`127.0.0.1`, `169.254.169.254`, локальная сеть) отсекаются до вызова `yt-dlp`.
2. **Rate Limiting**: Ограничение количества запросов по IP (по умолчанию 30 запросов в минуту) с поддержкой заголовков `X-Forwarded-For` за обратными прокси (Cloudflare, Render, Nginx).
3. **Лимит длительности**: Ограничение максимальной длительности видео (по умолчанию 4 часа — `14400` сек), предотвращающее перегрузку процессора долгими видео.
4. **Лимит размера файла**: Защита от переполнения диска файлами больше допустимого порога (`MAX_FILE_SIZE_MB=1024`).
5. **Безопасные имена файлов**: Очистка от спецсимволов пути (`../`, `:`, `*`, `?`) предотвращает Path Traversal.

---

## ⚙️ Переменные окружения (.env)

Скопируйте пример файла конфигурации:
```bash
cp .env.example .env
```

| Переменная | По умолчанию | Описание |
|---|---|---|
| `HOST` | `0.0.0.0` | IP-адрес для привязки веб-сервера |
| `PORT` | `8000` | Порт приложения |
| `PROXY_URL` | *пусто* | Прокси для обхода блокировок YouTube (поддерживает `IP:PORT:USER:PASS` или `http://user:pass@ip:port`) |
| `STORAGE_DIR` | `./downloads` | Директория временных файлов |
| `MAX_CONCURRENT_DOWNLOADS` | `1` | Ограничение параллельных слияний FFmpeg (1 для 512 МБ RAM) |
| `MAX_VIDEO_HEIGHT` | `720` | Максимальное разрешение видео (720p предотвращает OOM FFmpeg) |
| `MAX_DURATION_SECONDS`| `14400` | Макс. длительность видео (сек, 4 часа) |
| `MAX_FILE_SIZE_MB` | `1024` | Макс. размер файла (МБ, 1 ГБ) |
| `RATE_LIMIT_PER_MINUTE`| `30` | Лимит запросов в минуту с одного IP |
| `YTDLP_TIMEOUT_SECONDS`| `90` | Таймаут запросов к YouTube |
| `CLEANUP_INTERVAL_MINUTES`| `15` | Интервал проверки старых файлов |
| `FILE_RETENTION_MINUTES`| `30` | Время жизни временных файлов |
| `CORS_ORIGINS` | `*` | Разрешенные домены CORS |

---

## 🛡️ Оптимизации для Render Free (512 МБ RAM, 0.5 CPU)

Бесплатный тариф Render Free имеет жесткий лимит оперативной памяти в **512 МБ**. Превышение этого лимита приводит к немедленному завершению процесса сигналом `SIGKILL` (Out of Memory). В проекте реализован комплекс защитных механизмов:

1. **Сериализация загрузок (`MAX_CONCURRENT_DOWNLOADS=1`)**:
   - Параллельное слияние двух потоков 1080p в FFmpeg требует до 600-800 МБ RAM.
   - Сервер использует `threading.Semaphore(1)`. Если второй пользователь запускает скачивание, сервер не падает, а возвращает HTTP 503 с вежливым сообщением подождать 1 минуту.
2. **Ограничение разрешения (`MAX_VIDEO_HEIGHT=720`)**:
   - По умолчанию максимальное качество ограничено 720p HD. Это снижает пиковое потребление памяти FFmpeg до 150-250 МБ RAM.
   - При запросе 1080p сервер возвращает HTTP 400 с пояснением, защищая инстанс от краха.
3. **Прямой стриминг в браузер без `res.blob()`**:
   - Клиент не буферизирует видеофайлы (500 МБ - 1 ГБ) в JavaScript Heap браузера.
   - Браузер скачивает поток напрямую на диск пользователя через нативный загрузчик, предотвращая крах вкладок на смартфонах и ПК.
4. **Легковесный Pre-flight Check (`/api/check-download`)**:
   - Перед стартом скачивания фронтенд проверяет доступность слота, лимиты и наличие FFmpeg без нагрузки на сеть.
5. **Диагностика памяти в `/api/health`**:
   - Эндпоинт сообщает текущий Resident Set Size (`rss_mb`) и уровень риска (`oom_risk`: low, medium, high).

---

## 💻 Локальный запуск

### Вариант 1: Запуск через Python (без Docker)

#### Требования:
1. **Python 3.10+**
2. **FFmpeg**:
   - **Windows**: `winget install Gyan.FFmpeg` или скачайте с [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) и добавьте в `PATH`. Либо библиотека `imageio-ffmpeg` подхватится автоматически.
   - **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install -y ffmpeg`
   - **macOS**: `brew install ffmpeg`

#### Шаги:
```bash
# 1. Перейдите в папку проекта
cd youtube-analyzer-web

# 2. Создайте виртуальное окружение
python -m venv venv

# Активация на Windows:
venv\Scripts\activate
# Активация на Linux/macOS:
source venv/bin/activate

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Скопируйте конфигурацию
cp .env.example .env

# 5. Запустите сервер разработки
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Откройте в браузере: **`http://127.0.0.1:8000`**  
Документация Swagger API: **`http://127.0.0.1:8000/docs`**

---

### Вариант 2: Запуск через Docker Compose

Не требует локальной установки Python и FFmpeg — всё упаковано в контейнер:

```bash
# Сборка и запуск контейнера
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

Сервер будет доступен по адресу **`http://localhost:8000`**.

---

## 🚀 Деплой в облако (Production)

> [!IMPORTANT]
> **Почему нельзя использовать GitHub Pages?**  
> GitHub Pages поддерживает **только статические HTML/JS/CSS сайты** без серверного бэкенда. Для работы `yt-dlp`, извлечения видео и работы утилиты `ffmpeg` необходим полноценный сервер с поддержкой Docker или Python-рантайма.

Ниже приведены проверенные варианты бесплатного и доступного деплоя:

---

### Вариант А: Деплой на Render (Рекомендуемый, бесплатно)

1. Загрузите репозиторий на ваш GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<ваш-логин>/<имя-репозитория>.git
   git push -u origin main
   ```
2. Зайдите на [dashboard.render.com](https://dashboard.render.com/).
3. Нажмите **New +** → **Web Service** → подключите ваш репозиторий GitHub.
4. Выберите:
   - **Language**: `Docker`
   - **Branch**: `main`
   - **Region**: `Frankfurt (EU)` (или любой другой)
   - **Instance Type**: `Free`
5. В разделе **Environment Variables** (Переменные окружения):
   - Добавьте `PORT` = `10000` (Render использует порт 10000)
   - При необходимости добавьте `PROXY_URL` (см. раздел «Обход блокировок YouTube»)
6. Нажмите **Create Web Service**. Через 2 минуты сайт будет доступен по адресу `https://ваш-проект.onrender.com`.

*(Или используйте готовый файл `render.yaml` через раздел Blueprints на Render).*

---

### Вариант Б: Деплой на Railway

1. Перейдите на [railway.app](https://railway.app/) и авторизуйтесь через GitHub.
2. Нажмите **New Project** → **Deploy from GitHub repo** → выберите репозиторий.
3. Railway автоматически обнаружит `Dockerfile` и начнет сборку.
4. В разделе **Variables** добавьте переменные при необходимости (`PROXY_URL`).
5. В разделе **Settings** → **Networking** нажмите **Generate Domain**, чтобы получить публичный HTTPS-адрес.

---

### Вариант В: Деплой на Fly.io

1. Установите CLI: `powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"` (Windows) или `curl -L https://fly.io/install.sh | sh` (Linux/macOS).
2. Выполните вход: `fly auth login`.
3. В корне репозитория запустите:
   ```bash
   fly launch --no-deploy
   ```
   (Проект использует готовый файл `fly.toml`).
4. Разверните:
   ```bash
   fly deploy
   ```

---

### Вариант Г: Деплой на свой VPS (Ubuntu 22.04 / 24.04)

```bash
# 1. Клонируйте репозиторий на VPS
git clone https://github.com/<ваш-логин>/youtube-analyzer-web.git
cd youtube-analyzer-web

# 2. Создайте файл окружения
cp .env.example .env

# 3. Запустите через Docker Compose
docker compose up -d --build
```

Для настройки HTTPS через Nginx и Certbot:
```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 1024M;
        proxy_read_timeout 600s;
    }
}
```

---

## 🌐 Обход блокировок датацентров YouTube (HTTP 429)

Хостинги (AWS, Render, Hetzner, DigitalOcean) часто имеют диапазоны IP-адресов, которые YouTube временно блокирует ошибкой:
`HTTP Error 429: Too Many Requests` или `Sign in to confirm you're not a bot`.

Чтобы сервис бесперебойно работал в облаке:
1. Приобретите любой HTTP/SOCKS5 прокси (резидентный или IPv4/IPv6).
2. Задайте переменную окружения `PROXY_URL` в панели хостинга или в файле `.env`:
   ```env
   PROXY_URL=http://login:password@ip:port
   # Либо в формате analyze.py:
   # PROXY_URL=ip:port:login:password
   ```
Сервис автоматически конвертирует строку в формат, понятный для `yt-dlp`.

---

## 📡 Спецификация REST API

| Метод | Эндпоинт | Параметры | Описание |
|---|---|---|---|
| `GET` | `/api/health` | — | Проверка здоровья сервиса, статуса FFmpeg/прокси и RAM RSS |
| `GET` | `/api/check-download` | `url`, `kind`, `quality`, `format` | Pre-flight проверка готовности к скачиванию (слот, ffmpeg, лимиты) |
| `POST`| `/api/analyze` | JSON: `{"url": "..."}` | Получение метаданных, форматов, субтитров и размеров |
| `GET` | `/api/download/video` | `url`, `quality` (`1080p`, `720p`, `480p`, `360p`, `best`) | Стриминг видео с авто-удалением после передачи |
| `GET` | `/api/download/audio` | `url`, `format` (`mp3`, `m4a`) | Стриминг аудиофайла |
| `GET` | `/api/download/transcript` | `url`, `lang`, `format` (`txt`, `srt`) | Стриминг текста субтитров |

---

## 📄 Лицензия

Проект распространяется под открытой лицензией [MIT](LICENSE).
Вы можете свободно модифицировать, использовать и распространять данный код в личных и коммерческих целях.

`

---

### Файл: render.yaml

`yaml
services:
  - type: web
    name: yt-analyzer-web
    runtime: docker
    plan: free
    region: frankfurt
    dockerfilePath: ./Dockerfile
    healthCheckPath: /api/health
    envVars:
      - key: PORT
        value: 10000
      - key: PROXY_URL
        sync: false
      - key: MAX_DURATION_SECONDS
        value: 7200
      - key: MAX_FILE_SIZE_MB
        value: 500
      - key: MAX_CONCURRENT_DOWNLOADS
        value: 1
      - key: MAX_VIDEO_HEIGHT
        value: 720
      - key: RATE_LIMIT_PER_MINUTE
        value: 20

`

---

### Файл: requirements.txt

`text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
python-dotenv>=1.0.0
yt-dlp>=2024.3.10
imageio-ffmpeg>=0.4.9
pytest>=8.0.0


`

---
