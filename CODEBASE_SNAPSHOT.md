### Дерево каталогов проекта `youtube-analyzer-web` (v1.1.0 — Render Free Optimized)

```text
youtube-analyzer-web/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── cleanup.py
│   │   │   └── youtube.py
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── limiter.py
│   │   ├── main.py
│   │   └── schemas.py
│   └── tests/
│       └── test_reliability.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── .env.example
├── .gitignore
├── CODEBASE_SNAPSHOT.md
├── docker-compose.yml
├── Dockerfile
├── fly.toml
├── LICENSE
├── package.json
├── README.md
├── render.yaml
└── requirements.txt
```


### 1. Конфигурация и окружение

#### Файл: `.env.example`
```shell
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
```

#### Файл: `.gitignore`
```gitignore
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
```

#### Файл: `requirements.txt`
```text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
python-dotenv>=1.0.0
yt-dlp>=2024.3.10
imageio-ffmpeg>=0.4.9
pytest>=8.0.0
```

#### Файл: `package.json`
```json
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
```

#### Файл: `render.yaml`
```yaml
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
      - key: MALLOC_ARENA_MAX
        value: 2
      - key: PROXY_URL
        sync: false
      - key: COOKIES_TEXT
        sync: false
      - key: MAX_DURATION_SECONDS
        value: 7200
      - key: MAX_FILE_SIZE_MB
        value: 350
      - key: MAX_CONCURRENT_DOWNLOADS
        value: 1
      - key: MAX_VIDEO_HEIGHT
        value: 720
      - key: CLEANUP_INTERVAL_MINUTES
        value: 10
      - key: FILE_RETENTION_MINUTES
        value: 15
      - key: RATE_LIMIT_PER_MINUTE
        value: 20
```

#### Файл: `fly.toml`
```toml
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
```

#### Файл: `Dockerfile`
```dockerfile
# Multi-stage/Slim production Dockerfile optimized for Render Free (512MB RAM)
FROM python:3.11-slim

# Prevent Python from writing .pyc files, enable unbuffered logging,
# and cap glibc malloc arenas to 2 to prevent multithreaded memory fragmentation on 512MB RAM
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
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

# Install Python requirements (skipping duplicate 80MB imageio-ffmpeg wheel since system ffmpeg is installed)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    grep -vE '^(imageio-ffmpeg|pytest)' requirements.txt > requirements.prod.txt && \
    pip install --no-cache-dir -r requirements.prod.txt && \
    rm -f requirements.prod.txt

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

# Launch production server with single worker and tuned keep-alive for 512MB RAM
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 15"]
```

#### Файл: `docker-compose.yml`
```yaml
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
```

#### Файл: `LICENSE`
```text
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
```


### 2. Бэкенд (FastAPI, yt-dlp, FFmpeg)

#### Файл: `backend/app/__init__.py`
```python
"""YouTube Video Analyzer & Downloader Backend Application Package."""

__version__ = "1.0.0"
```

#### Файл: `backend/app/config.py`
```python
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
```

#### Файл: `backend/app/limiter.py`
```python
"""Security validations and thread-safe in-memory rate limiting."""

import re
import time
import threading
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException, status
from .config import settings

# Strict 11-character YouTube video ID pattern
VIDEO_ID_EXACT_REGEX = re.compile(r'^[a-zA-Z0-9_-]{11}$')


def validate_youtube_url(url: str) -> str:
    """
    Validates the YouTube URL, prevents SSRF attacks, and returns a normalized canonical URL.
    Supports standard watch URLs (regardless of query param order), shorts, live, embed, v,
    youtu.be, and music.youtube.com.
    Raises HTTPException(400) if the URL is invalid or unsafe.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL видео не может быть пустым."
        )

    url = url.strip()

    # Prepend https:// if protocol was omitted
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат URL."
        )

    # Reject URLs with embedded credentials (user:pass@host) to prevent SSRF tricks
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат URL: запрещены учетные данные в адресе."
        )

    # Allowed hostnames
    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }

    hostname = (parsed.hostname or "").lower()
    if hostname not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Разрешены только ссылки на YouTube (youtube.com или youtu.be)."
        )

    path = parsed.path or ""
    path_lower = path.lower()
    query_params = parse_qs(parsed.query)

    # Check for pure playlists or channels without a specific video ID
    if path_lower == "/playlist" or path_lower.startswith("/playlist/") or ("list" in query_params and "v" not in query_params and hostname not in {"youtu.be", "www.youtu.be"}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Скачивание плейлистов целиком не поддерживается. Пожалуйста, укажите ссылку на конкретное видео."
        )
    if path_lower.startswith(("/@", "/channel/", "/c/", "/user/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылки на каналы не поддерживаются. Пожалуйста, укажите ссылку на конкретное видео."
        )

    video_id = None

    if hostname in {"youtu.be", "www.youtu.be"}:
        # Format: https://youtu.be/<11-char-id>
        segments = [seg for seg in path.split("/") if seg]
        if segments:
            video_id = segments[0]
    else:
        # Format 1: /watch?v=<11-char-id> (supports v= anywhere in query string)
        if path_lower in {"/watch", "/watch/"} and "v" in query_params:
            v_list = query_params.get("v")
            if v_list:
                video_id = v_list[0]
        else:
            # Format 2: /shorts/<id>, /live/<id>, /embed/<id>, /v/<id>
            segments = [seg for seg in path.split("/") if seg]
            if len(segments) >= 2 and segments[0].lower() in {"shorts", "live", "embed", "v"}:
                video_id = segments[1]

    if not video_id or not VIDEO_ID_EXACT_REGEX.match(video_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось распознать корректный 11-символьный идентификатор видео YouTube в ссылке."
        )

    # Return normalized canonical URL
    return f"https://www.youtube.com/watch?v={video_id}"


class InMemoryRateLimiter:
    """Thread-safe sliding-window in-memory rate limiter per client IP with automatic memory pruning."""

    def __init__(self, limit_per_minute: int = 30):
        self.limit = limit_per_minute
        self.window = 60.0  # seconds
        self.requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._last_full_prune = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Extracts client IP, respecting forward headers from proxies like Render/Cloudflare."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    def is_allowed(self, request: Request) -> bool:
        """Checks if current client IP is allowed under the rate limit."""
        ip = self._get_client_ip(request)
        now = time.time()

        with self._lock:
            # Periodic global prune of stale IP keys every 5 minutes to prevent memory growth
            if now - self._last_full_prune > 300.0:
                stale_ips = [
                    k for k, ts_list in self.requests.items()
                    if not ts_list or (now - ts_list[-1] >= self.window)
                ]
                for k in stale_ips:
                    self.requests.pop(k, None)
                self._last_full_prune = now

            timestamps = self.requests.get(ip, [])
            valid_timestamps = [t for t in timestamps if now - t < self.window]

            if len(valid_timestamps) >= self.limit:
                self.requests[ip] = valid_timestamps
                return False

            valid_timestamps.append(now)
            self.requests[ip] = valid_timestamps
            return True

    def check(self, request: Request):
        """Raises HTTPException(429) if rate limit is exceeded."""
        if not self.is_allowed(request):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много запросов. Лимит сервера: {self.limit} запросов в минуту."
            )


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(limit_per_minute=settings.RATE_LIMIT_PER_MINUTE)
```

#### Файл: `backend/app/schemas.py`
```python
"""Pydantic data models for request and response serialization."""

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Payload to request video analysis."""
    url: str = Field(..., description="YouTube video URL (watch, shorts, youtu.be, embed, music)")


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
    """Preset video download choice with estimated size and availability flag."""
    quality: str  # 1080p, 720p, 480p, 360p, best
    label: str
    ext: str = "mp4"
    filesize_approx_mb: Optional[float] = None
    filesize_str: str
    download_url: str
    available: bool = True


class AudioOption(BaseModel):
    """Preset audio download choice with estimated size."""
    format: str  # mp3, m4a
    label: str
    bitrate_kbps: int
    filesize_approx_mb: Optional[float] = None
    filesize_str: str
    download_url: str
    available: bool = True


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
```

#### Файл: `backend/app/main.py`
```python
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
    version="1.1.0",
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
```

#### Файл: `backend/app/services/__init__.py`
```python
"""Services package."""
```

#### Файл: `backend/app/services/cleanup.py`
```python
"""Temporary file cleanup utilities to prevent disk exhaustion."""

import time
import shutil
import logging
import threading
from pathlib import Path

logger = logging.getLogger("cleanup")

# Protected system files that must NEVER be deleted by cleanup (module-level constant)
PROTECTED_FILENAMES = {"cookies.txt", "runtime_cookies.txt", ".gitkeep", "README.md"}


def delete_file_safely(file_or_dir_path: str | Path):
    """Safely removes a file or directory without raising exceptions."""
    try:
        p = Path(file_or_dir_path)
        if p.name in PROTECTED_FILENAMES:
            return
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
    interval_secs = max(interval_minutes, 1) * 60
    retention_secs = max(retention_minutes, 1) * 60

    # Perform an immediate cleanup pass of any leftover expired files from previous runs
    try:
        cleanup_old_files(storage_dir, retention_secs)
    except Exception as e:
        logger.debug(f"Initial cleanup error: {e}")

    def worker():
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
```

#### Файл: `backend/app/services/youtube.py`
```python
"""YouTube extraction and media downloading service using yt-dlp and ffmpeg."""

import os
import re
import html
import time
import uuid
import shutil
import logging
import threading
import urllib.parse
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
_subtitles_semaphore = threading.Semaphore(max(3, settings.MAX_CONCURRENT_DOWNLOADS * 3))
_active_downloads_count = 0
_active_downloads_lock = threading.Lock()
_cookies_lock = threading.Lock()

# 60-second in-memory metadata cache to prevent redundant extract_info calls
_INFO_CACHE: dict[str, Tuple[float, dict]] = {}
_INFO_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 60.0
_MAX_CACHE_ENTRIES = 64


def get_cached_or_extract_info(url: str, extra_opts: Optional[dict] = None) -> dict:
    """
    Retrieves video info dictionary from in-memory cache or extracts via yt-dlp.
    Cached for 60 seconds to eliminate redundant network extraction between pre-check and download.
    Bounded to _MAX_CACHE_ENTRIES to protect 512MB RAM on Render Free.
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
        # Evict oldest entry if cache exceeds max size
        if len(_INFO_CACHE) >= _MAX_CACHE_ENTRIES:
            oldest_key = min(_INFO_CACHE.keys(), key=lambda k: _INFO_CACHE[k][0])
            _INFO_CACHE.pop(oldest_key, None)
        _INFO_CACHE[url] = (time.time(), info)

    return info


def get_active_downloads_count() -> int:
    """Returns the number of currently active media download jobs."""
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
    1. Checks server limits (FFmpeg, active download semaphore, max height cap).
    2. Checks video accessibility (extracts/uses cached metadata, detects private/429/403/live/duration).
    3. Checks format/quality availability (verifies video height <= requested quality).
    Returns: (is_ok: bool, message: str, title: Optional[str])
    """
    # 1. Server constraints - cheap fail-fast checks
    if kind == "video" and quality == "1080p" and settings.MAX_VIDEO_HEIGHT and settings.MAX_VIDEO_HEIGHT < 1080:
        return (
            False,
            f"Качество 1080p отключено из-за ограничения памяти сервера (512 МБ RAM). "
            f"Максимальное допустимое разрешение: {settings.MAX_VIDEO_HEIGHT}p.",
            None,
        )

    if not get_ffmpeg_path() and (kind == "video" or format_str == "mp3"):
        return False, "FFmpeg не установлен на сервере. Слияние аудио и видео невозможно.", None

    if kind in ("video", "audio") and get_active_downloads_count() >= settings.MAX_CONCURRENT_DOWNLOADS:
        return (
            False,
            "Сервер занят другой загрузкой. Из-за лимита памяти (512 МБ) "
            "загрузки выполняются строго по очереди. Попробуйте через несколько минут.",
            None,
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

    # Check live stream / upcoming status
    if info.get("is_live"):
        return False, "Это видео является прямым эфиром (Live stream). Скачивание станет доступно после завершения трансляции.", title
    if info.get("live_status") == "is_upcoming":
        return False, "Это видео является запланированной премьерой. Скачивание пока недоступно.", title

    # Check duration limit
    duration = info.get("duration") or 0
    if duration > settings.MAX_DURATION_SECONDS:
        max_hours = settings.MAX_DURATION_SECONDS // 3600
        return (
            False,
            f"Длительность видео ({format_duration(duration)}) превышает допустимый лимит сервера ({max_hours} ч).",
            title,
        )

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
    Prioritizes H.264 (avc1) + AAC (m4a) for instant low-RAM MP4 stream-copy merging on Render Free,
    then falls back to any codec within the height cap.
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
        return "bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

    # Strictly under target_h: no branch can exceed target_h
    steps = [h for h in (1080, 720, 480, 360) if h <= target_h]
    parts = []
    for h in steps:
        parts.append(f"bestvideo[height<={h}][vcodec^=avc]+bestaudio[ext=m4a]")
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
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', name or "")
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


def _prepare_writable_cookiefile() -> Optional[str]:
    """
    Ensures yt-dlp always receives a WRITABLE cookiefile path inside STORAGE_DIR.
    Prevents 'OSError: [Errno 30] Read-only file system' when COOKIES_FILE is mounted
    read-only (e.g. Render Secret Files at /etc/secrets/cookies.txt or Docker :ro volumes),
    because yt-dlp writes updated session cookies back to cookiefile on exit.
    """
    runtime_cookies = settings.STORAGE_DIR / "runtime_cookies.txt"

    with _cookies_lock:
        if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
            try:
                src_path = Path(settings.COOKIES_FILE).resolve()
                if src_path != runtime_cookies.resolve():
                    # Copy if runtime_cookies doesn't exist or source was updated
                    if not runtime_cookies.exists() or src_path.stat().st_mtime > runtime_cookies.stat().st_mtime:
                        shutil.copyfile(src_path, runtime_cookies)
                return str(runtime_cookies)
            except Exception as e:
                logger.warning(f"Could not copy COOKIES_FILE to writable storage: {e}")
                return settings.COOKIES_FILE

        elif settings.COOKIES_TEXT:
            try:
                raw_text = settings.COOKIES_TEXT.strip()
                # Normalize escaped newlines often pasted into cloud dashboard env vars
                if "\\n" in raw_text and "\n" not in raw_text:
                    raw_text = raw_text.replace("\\n", "\n")
                if not raw_text.startswith("# Netscape HTTP Cookie File"):
                    raw_text = "# Netscape HTTP Cookie File\n" + raw_text
                if not runtime_cookies.exists() or runtime_cookies.read_text(encoding="utf-8", errors="ignore").strip() != raw_text.strip():
                    runtime_cookies.write_text(raw_text + "\n", encoding="utf-8")
                return str(runtime_cookies)
            except Exception as e:
                logger.warning(f"Could not write COOKIES_TEXT to runtime_cookies.txt: {e}")

    return None


def get_ydl_base_opts(extra_opts: Optional[dict] = None) -> dict:
    """Constructs base yt-dlp options including proxy, cookies, retries, single-thread FFmpeg, and timeouts."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "socket_timeout": settings.YTDLP_TIMEOUT_SECONDS,
        "retries": 5,
        "fragment_retries": 5,
        "continuedl": True,
        "nopart": True,  # Avoid extra .part rename overhead on container tmpfs
        "http_chunk_size": 10485760,  # 10MB chunk size prevents YouTube throttling
        # Limit FFmpeg to 1 thread to prevent 8-16 core host threadpool RAM spikes on Render Free (512MB)
        "postprocessor_args": {
            "ffmpeg": ["-threads", "1"],
        },
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

    # Authentication & Cookies support (writable runtime copy prevents Read-Only FS crash)
    writable_cookiefile = _prepare_writable_cookiefile()
    if writable_cookiefile:
        opts["cookiefile"] = writable_cookiefile
    elif settings.COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (settings.COOKIES_FROM_BROWSER, None, None, None)

    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg_bin) if os.path.isfile(ffmpeg_bin) else ffmpeg_bin

    if extra_opts:
        opts.update(extra_opts)

    return opts


def _raise_for_ydl_error(e: Exception, context_action: str = "обработке видео"):
    """Translates yt-dlp exceptions into user-friendly HTTPExceptions with proper status codes."""
    error_msg = sanitize_error_message(e)
    if "429" in error_msg or "Too Many Requests" in error_msg:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "YouTube заблокировал IP-адрес сервера (HTTP 429 Too Many Requests). "
                "Для работы на серверах хостинга требуется настроить PROXY_URL или COOKIES в .env."
            )
        )
    elif "Private video" in error_msg or "Sign in" in error_msg or "confirm you're not a bot" in error_msg:
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Видео недоступно в запрошенном качестве (лимит сервера ≤{settings.MAX_VIDEO_HEIGHT}p) "
                "или YouTube ограничил отдачу потоков для данного региона."
            )
        )
    elif "File is larger than max-filesize" in error_msg:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер видеопотока превышает допустимый лимит сервера ({settings.MAX_FILE_SIZE_MB} МБ)."
        )
    elif "Video unavailable" in error_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Видео недоступно, удалено или заблокировано правообладателем."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка yt-dlp при {context_action}: {error_msg}"
        )


def extract_video_metadata(url: str) -> AnalyzeResponse:
    """
    Extracts complete metadata, available formats, estimated sizes,
    and available subtitle tracks for a YouTube video.
    """
    try:
        meta = get_cached_or_extract_info(url)
    except yt_dlp.utils.DownloadError as e:
        _raise_for_ydl_error(e, "анализе видео")
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

    available_heights = set()
    for f in formats:
        f_id = str(f.get("format_id", ""))
        ext = f.get("ext", "mp4")
        h = f.get("height")
        if h and isinstance(h, int) and h > 0:
            available_heights.add(h)
        res = f.get("resolution") or (f"{f.get('width')}x{h}" if f.get('width') else "audio only")
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
    encoded_url = urllib.parse.quote(url, safe="")

    # 3. Build preset Video Options: best, 1080p, 720p, 480p, 360p
    server_cap = settings.MAX_VIDEO_HEIGHT or 1080
    if settings.MAX_VIDEO_HEIGHT and settings.MAX_VIDEO_HEIGHT < 1080:
        quality_specs = [
            ("best", f"Наилучшее доступное качество (до {settings.MAX_VIDEO_HEIGHT}p, Render Free)", settings.MAX_VIDEO_HEIGHT, True),
            ("1080p", f"Full HD 1080p (MP4) — отключено (лимит {settings.MAX_VIDEO_HEIGHT}p на сервере)", 1080, False),
            ("720p", "HD 720p (MP4)", 720, True),
            ("480p", "SD 480p (MP4)", 480, True),
            ("360p", "Низкое 360p (MP4)", 360, True),
        ]
    else:
        quality_specs = [
            ("best", "Наилучшее доступное качество (Original/Best)", None, True),
            ("1080p", "Full HD 1080p (MP4)", 1080, True),
            ("720p", "HD 720p (MP4)", 720, True),
            ("480p", "SD 480p (MP4)", 480, True),
            ("360p", "Низкое 360p (MP4)", 360, True),
        ]

    video_options: list[VideoOption] = []
    for q_key, q_label, max_h, is_allowed_by_server in quality_specs:
        # Check if any video stream exists at or below the requested cap
        effective_cap = max_h or server_cap
        has_compatible_stream = (not available_heights) or any(0 < h <= effective_cap for h in available_heights)
        is_available = bool(is_allowed_by_server and has_compatible_stream)

        best_match_size = None
        for f in formats:
            h = f.get("height")
            if max_h is None or (h and h <= max_h):
                f_size = f.get("filesize") or f.get("filesize_approx")
                if f_size and (best_match_size is None or f_size > best_match_size):
                    best_match_size = f_size

        if not best_match_size and duration > 0:
            bitrate_map = {1080: 3500, 720: 2000, 480: 1000, 360: 600}
            target_kbps = bitrate_map.get(max_h, 2500) if max_h else 2500
            best_match_size = duration * (target_kbps * 1024 / 8)

        total_bytes = (best_match_size or 0) + (audio_est_bytes if max_h else 0)
        total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes > 0 else None

        video_options.append(
            VideoOption(
                quality=q_key,
                label=q_label,
                ext="mp4",
                filesize_approx_mb=total_mb,
                filesize_str=format_bytes(total_bytes) if is_available and total_bytes else ("Недоступно" if not is_available else "Размер уточняется"),
                download_url=f"/api/download/video?url={encoded_url}&quality={q_key}",
                available=is_available,
            )
        )

    # 4. Build preset Audio Options: MP3 (320k) and M4A
    mp3_bytes = duration * (320 * 1024 / 8) if duration > 0 else None
    m4a_bytes = duration * (128 * 1024 / 8) if duration > 0 else None
    ffmpeg_ok = bool(get_ffmpeg_path())

    audio_options: list[AudioOption] = [
        AudioOption(
            format="mp3",
            label="Аудио MP3 (Высокое качество, 320 kbps)",
            bitrate_kbps=320,
            filesize_approx_mb=round(mp3_bytes / (1024 * 1024), 1) if mp3_bytes else None,
            filesize_str=format_bytes(mp3_bytes) if mp3_bytes else "Размер уточняется",
            download_url=f"/api/download/audio?url={encoded_url}&format=mp3",
            available=ffmpeg_ok,
        ),
        AudioOption(
            format="m4a",
            label="Аудио M4A (Оригинальный AAC-поток YouTube)",
            bitrate_kbps=128,
            filesize_approx_mb=round(m4a_bytes / (1024 * 1024), 1) if m4a_bytes else None,
            filesize_str=format_bytes(m4a_bytes) if m4a_bytes else "Размер уточняется",
            download_url=f"/api/download/audio?url={encoded_url}&format=m4a",
            available=True,
        ),
    ]

    # 5. Build Subtitle / Transcript options
    subtitle_options: list[SubtitleOption] = []
    seen_langs = set()

    # Manual subtitles first
    manual_subs = meta.get("subtitles") or {}
    for lang, track_list in manual_subs.items():
        if lang == "live_chat":
            continue
        name = track_list[0].get("name", lang) if track_list else lang
        seen_langs.add(lang)
        encoded_lang = urllib.parse.quote(lang, safe="")
        subtitle_options.append(
            SubtitleOption(
                lang=lang,
                name=f"{name} (ручные)",
                is_auto=False,
                txt_url=f"/api/download/transcript?url={encoded_url}&lang={encoded_lang}&format=txt",
                srt_url=f"/api/download/transcript?url={encoded_url}&lang={encoded_lang}&format=srt",
            )
        )

    # Automatic captions next
    auto_subs = meta.get("automatic_captions") or {}
    for lang, track_list in auto_subs.items():
        if lang not in seen_langs and lang != "live_chat":
            name = track_list[0].get("name", lang) if track_list else lang
            encoded_lang = urllib.parse.quote(lang, safe="")
            subtitle_options.append(
                SubtitleOption(
                    lang=lang,
                    name=f"{name} (автогенерация)",
                    is_auto=True,
                    txt_url=f"/api/download/transcript?url={encoded_url}&lang={encoded_lang}&format=txt",
                    srt_url=f"/api/download/transcript?url={encoded_url}&lang={encoded_lang}&format=srt",
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
        channel=meta.get("channel") or meta.get("uploader") or "Неизвестный канал",
        channel_url=meta.get("channel_url") or meta.get("uploader_url"),
        duration=int(duration),
        duration_str=format_duration(duration),
        upload_date=formatted_date,
        view_count=meta.get("view_count"),
        thumbnail=meta.get("thumbnail"),
        original_url=url,
        description=(meta.get("description") or "")[:1500],
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
        out_template = str(job_dir / "video_%(height)sp.%(ext)s")

        ydl_opts = get_ydl_base_opts({
            "format": fmt,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
            "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = sanitize_filename(info.get("title", "video"))
        except yt_dlp.utils.DownloadError as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            _raise_for_ydl_error(e, f"скачивании видео ({quality})")
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
        downloaded_files = [f for f in job_dir.glob("*.mp4") if f.is_file()]
        if not downloaded_files:
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

        out_template = str(job_dir / "audio.%(ext)s")

        if audio_format.lower() == "mp3":
            ydl_opts = get_ydl_base_opts({
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": out_template,
                "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
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
                "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
            })
            expected_ext = ".m4a"
            mime_type = "audio/mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = sanitize_filename(info.get("title", "audio"))
        except yt_dlp.utils.DownloadError as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            _raise_for_ydl_error(e, f"скачивании аудио ({audio_format})")
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            logger.error(f"Error downloading audio {url} [{audio_format}]: {sanitized_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось скачать аудио: {sanitized_err}"
            )

        # Locate generated output file
        downloaded_files = [f for f in job_dir.glob(f"*{expected_ext}") if f.is_file()]
        if not downloaded_files:
            downloaded_files = [f for f in job_dir.iterdir() if f.is_file()]

        if not downloaded_files:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Результирующий аудиофайл не был создан."
            )

        target_file = downloaded_files[0]
        file_size_mb = target_file.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер аудиофайла ({file_size_mb:.1f} МБ) превышает лимит сервера ({settings.MAX_FILE_SIZE_MB} МБ)."
            )

        download_filename = f"{title}.{audio_format.lower()}"
        return target_file, download_filename, mime_type


def vtt_to_srt(vtt_content: str) -> str:
    """
    Pure-Python converter from WebVTT (.vtt) to standard SubRip (.srt).
    Avoids spawning an FFmpeg child process on Render Free 512MB RAM.
    """
    blocks = []
    current_lines = []
    current_ts = None

    for raw_line in vtt_content.splitlines():
        line = raw_line.strip()
        if not line:
            if current_ts and current_lines:
                blocks.append((current_ts, "\n".join(current_lines)))
            current_ts = None
            current_lines = []
            continue

        # Skip WEBVTT header and metadata lines
        if (
            line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("Style:")
            or line.startswith("NOTE")
        ):
            continue

        # Match timestamp line: 00:00:01.000 --> 00:00:04.000 (or MM:SS.000)
        if "-->" in line and re.search(r"\d{2}:\d{2}", line):
            parts = line.split("-->")
            if len(parts) >= 2:
                start_raw = parts[0].strip().split()[0].replace(".", ",")
                end_raw = parts[1].strip().split()[0].replace(".", ",")
                if start_raw.count(":") == 1:
                    start_raw = "00:" + start_raw
                if end_raw.count(":") == 1:
                    end_raw = "00:" + end_raw
                current_ts = f"{start_raw} --> {end_raw}"
            continue

        # Skip pure cue numeric identifiers before timestamp
        if current_ts is None and re.match(r"^\d+$", line):
            continue

        if current_ts:
            clean = re.sub(r"<[^>]+>", "", line).strip()
            clean = html.unescape(clean)
            if clean and (not current_lines or clean != current_lines[-1]):
                current_lines.append(clean)

    if current_ts and current_lines:
        blocks.append((current_ts, "\n".join(current_lines)))

    srt_out = []
    for idx, (ts, text) in enumerate(blocks, start=1):
        srt_out.append(f"{idx}\n{ts}\n{text}")
    return "\n\n".join(srt_out) if srt_out else vtt_content


def srt_to_clean_txt(srt_content: str) -> str:
    """
    Cleans an SRT or WebVTT string into pure legible text:
    removes WEBVTT headers, numeric indexes, timestamps, HTML tags, entities,
    and duplicate consecutive lines.
    Preserves natural repetition of lyrics and dialogue while removing rolling caption artifacts.
    """
    lines = []
    prev_line = ""
    for raw_line in srt_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip WebVTT headers and metadata
        if (
            line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("Style:")
            or line.startswith("NOTE")
        ):
            continue
        # Skip numeric index lines
        if re.match(r"^\d+$", line):
            continue
        # Skip timestamp lines (00:00:01,000 --> 00:00:04,000 or 00:01.000 --> 00:04.000)
        if "-->" in line or re.match(r"^\d{2}:\d{2}(:\d{2})?[.,]\d{3}", line):
            continue
        # Remove HTML-like markup and inline VTT timing tags (<00:00:01.000>, <c>, <font>, etc.)
        clean = re.sub(r"<[^>]+>", "", line).strip()
        clean = html.unescape(clean).strip()
        # Deduplicate ONLY consecutive identical lines (YouTube auto-subtitles rolling artifact),
        # preserving recurring phrases, songs, and dialogue throughout the video
        if clean and clean != prev_line:
            lines.append(clean)
            prev_line = clean

    return "\n".join(lines)


def _find_matching_sub_file(job_dir: Path, target_lang: str) -> Optional[Path]:
    """Finds downloaded subtitle file matching target_lang first, then any .srt/.vtt candidate."""
    exact_matches = (
        list(job_dir.glob(f"*.{target_lang}.srt"))
        + list(job_dir.glob(f"*.{target_lang}.vtt"))
    )
    if exact_matches:
        return exact_matches[0]
    all_candidates = list(job_dir.glob("*.srt")) + list(job_dir.glob("*.vtt"))
    return all_candidates[0] if all_candidates else None


def download_subtitles_file(url: str, lang: str = "ru", format_type: str = "txt") -> Tuple[Path, str, str]:
    """
    Extracts subtitles (exact language manual first, then exact language auto, then fallback)
    using yt-dlp. Uses a separate lightweight semaphore so transcript preview/download is not
    blocked by long FFmpeg video downloads.
    Outputs clean .txt (without timestamps/duplicates) or standard .srt.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
    acquired = _subtitles_semaphore.acquire(blocking=True, timeout=15.0)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервер перегружен запросами субтитров. Пожалуйста, повторите попытку через несколько секунд."
        )

    try:
        unique_job_id = f"subs_{uuid.uuid4().hex[:10]}"
        job_dir = settings.STORAGE_DIR / unique_job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        out_template = str(job_dir / "subtitles")
        found_sub: Optional[Path] = None
        title = "subtitles"

        # Determine cached title if available to avoid extra metadata wait
        with _INFO_CACHE_LOCK:
            cached_entry = _INFO_CACHE.get(url)
            if cached_entry:
                title = sanitize_filename(cached_entry[1].get("title", "transcript"))

        # Step 1: Exact requested language in manual subtitles
        ydl_opts_manual = get_ydl_base_opts({
            "skip_download": True,
            "writesubtitles": True,
            "subtitleslangs": [lang],
            "subtitlesformat": "srt/vtt/best",
            "outtmpl": out_template,
        })
        try:
            with yt_dlp.YoutubeDL(ydl_opts_manual) as ydl:
                info = ydl.extract_info(url, download=True)
                if info and info.get("title"):
                    title = sanitize_filename(info.get("title", "transcript"))
        except Exception as e:
            logger.warning(f"Error checking manual subs [{lang}]: {sanitize_error_message(e)}")

        found_sub = _find_matching_sub_file(job_dir, lang)

        # Step 2: Exact requested language in automatic captions
        if not found_sub:
            ydl_opts_auto = get_ydl_base_opts({
                "skip_download": True,
                "writeautomaticsub": True,
                "subtitleslangs": [lang],
                "subtitlesformat": "srt/vtt/best",
                "outtmpl": out_template,
            })
            try:
                with yt_dlp.YoutubeDL(ydl_opts_auto) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info and info.get("title"):
                        title = sanitize_filename(info.get("title", "transcript"))
            except Exception as e:
                logger.warning(f"Error checking auto subs [{lang}]: {sanitize_error_message(e)}")

            found_sub = _find_matching_sub_file(job_dir, lang)

        # Step 3: Fallback to ru/en if default language was requested and not found directly
        if not found_sub and lang in ("ru", "en"):
            fallback_langs = ["ru", "en"]
            ydl_opts_fallback = get_ydl_base_opts({
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": fallback_langs,
                "subtitlesformat": "srt/vtt/best",
                "outtmpl": out_template,
            })
            try:
                with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
                    ydl.extract_info(url, download=True)
            except Exception as e:
                logger.warning(f"Error checking fallback subs: {sanitize_error_message(e)}")

            found_sub = _find_matching_sub_file(job_dir, lang)

        if not found_sub:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Субтитры для языка '{lang}' не найдены у данного видео."
            )

        # Read raw subtitle content
        try:
            content = found_sub.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            sanitized_err = sanitize_error_message(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка чтения субтитров: {sanitized_err}"
            )

        safe_lang = re.sub(r"[^a-zA-Z0-9_-]", "", lang) or "sub"
        if format_type.lower() == "txt":
            clean_text = srt_to_clean_txt(content)
            txt_path = job_dir / f"{title}_{safe_lang}.txt"
            txt_path.write_text(clean_text, encoding="utf-8")
            return txt_path, f"{title}_{safe_lang}.txt", "text/plain; charset=utf-8"
        else:  # srt
            out_srt = job_dir / f"{title}_{safe_lang}.srt"
            if found_sub.suffix.lower() == ".vtt" or content.lstrip().startswith("WEBVTT"):
                srt_text = vtt_to_srt(content)
                out_srt.write_text(srt_text, encoding="utf-8")
            elif found_sub != out_srt:
                found_sub.rename(out_srt)
            return out_srt, f"{title}_{safe_lang}.srt", "text/plain; charset=utf-8"
    finally:
        _subtitles_semaphore.release()
```

#### Файл: `backend/tests/test_reliability.py`
```python
"""
Automated reliability and regression test suite for youtube-analyzer-web.
Covers Render Free 512MB RAM protections and core functionality:
- Concurrency serialization (MAX_CONCURRENT_DOWNLOADS=1, 503 rejection)
- Height capping and elimination of unconstrained /best and /worst, with H.264 priority
- Error message credential sanitization (no sensitive data leaks)
- Pre-flight check endpoint (/api/check-download) with video accessibility, 1080p cap, live stream & duration guard
- cgroup/RSS memory diagnostics (/api/health)
- Cyrillic Content-Disposition latin-1 HTTP header safety
- WebVTT to SRT conversion and clean TXT transcript extraction
- Writable cookiefile copy for read-only mounts (/etc/secrets/cookies.txt)
- Extended URL validation (query param order, music.youtube.com, shorts, live)
"""

import os
import re
import sys
import tempfile
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
from backend.app.main import app, make_content_disposition
from backend.app.services.cleanup import PROTECTED_FILENAMES
from backend.app.services.youtube import (
    sanitize_error_message,
    _build_format_selector,
    DownloadSlot,
    get_active_downloads_count,
    check_download_feasibility,
    srt_to_clean_txt,
    vtt_to_srt,
    _prepare_writable_cookiefile,
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
        parts = selector.split("/")
        for p in parts:
            self.assertTrue(
                "height<=720" in p or "height<=480" in p or "height<=360" in p,
                f"Part {p} violates height cap 720!"
            )
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

    def test_url_validation_non_first_v_param_and_music(self):
        """Mobile share URLs with ?feature=shared&v=... and music.youtube.com must be accepted."""
        url1 = "https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ"
        url2 = "https://music.youtube.com/watch?v=dQw4w9WgXcQ&si=abcdef"
        url3 = "youtu.be/dQw4w9WgXcQ?t=42"
        self.assertEqual(validate_youtube_url(url1), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(validate_youtube_url(url2), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(validate_youtube_url(url3), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

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

    def test_check_download_feasibility_1080p_rejected_on_720p_cap(self):
        """Pre-check immediately rejects 1080p when server MAX_VIDEO_HEIGHT is 720."""
        with patch.object(settings, "MAX_VIDEO_HEIGHT", 720):
            ok, msg, _ = check_download_feasibility(
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                kind="video",
                quality="1080p"
            )
            self.assertFalse(ok)
            self.assertIn("1080p отключено", msg)

    # 6. Cleanup protected filenames
    def test_cleanup_protected_files(self):
        """Ensures cookies.txt, runtime_cookies.txt, .gitkeep, README.md are strictly protected."""
        self.assertIn("cookies.txt", PROTECTED_FILENAMES)
        self.assertIn("runtime_cookies.txt", PROTECTED_FILENAMES)
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

    # 9. Cyrillic Content-Disposition Latin-1 encoding safety
    def test_content_disposition_cyrillic_latin1_safe(self):
        """Ensures Cyrillic filenames do not crash Starlette latin-1 header encoding."""
        header = make_content_disposition("Разбор_полетов_720p.mp4")
        # Must encode cleanly in latin-1 without UnicodeEncodeError
        encoded = header.encode("latin-1")
        self.assertIsInstance(encoded, bytes)
        self.assertIn("filename*=UTF-8''", header)

    # 10. WebVTT cleaning and SRT conversion
    def test_vtt_and_srt_cleaning(self):
        """Ensures WEBVTT metadata, timestamps, HTML entities, and rolling duplicates are stripped."""
        sample_vtt = (
            "WEBVTT\n"
            "Kind: captions\n"
            "Language: ru\n\n"
            "00:00:01.000 --> 00:00:03.500 align:start position:0%\n"
            "<c>Привет</c> &amp; добро пожаловать!\n\n"
            "00:00:03.500 --> 00:00:05.000\n"
            "Привет &amp; добро пожаловать!\n"
            "Вторая строка текста&#39;\n"
        )
        clean_txt = srt_to_clean_txt(sample_vtt)
        self.assertEqual(clean_txt, "Привет & добро пожаловать!\nВторая строка текста'")

        converted_srt = vtt_to_srt(sample_vtt)
        self.assertIn("1\n00:00:01,000 --> 00:00:03,500\nПривет & добро пожаловать!", converted_srt)
        self.assertNotIn("WEBVTT", converted_srt)

    # 11. Writable runtime cookies from COOKIES_TEXT
    def test_writable_cookies_from_text(self):
        """Ensures COOKIES_TEXT is normalized and written to a writable file in STORAGE_DIR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(settings, "STORAGE_DIR", tmp_path), \
                 patch.object(settings, "COOKIES_FILE", ""), \
                 patch.object(settings, "COOKIES_TEXT", ".youtube.com\\tTRUE\\t/\\tTRUE\\t0\\tSID\\t12345"):
                cookie_file = _prepare_writable_cookiefile()
                self.assertIsNotNone(cookie_file)
                content = Path(cookie_file).read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# Netscape HTTP Cookie File"))
                self.assertIn(".youtube.com", content)


if __name__ == "__main__":
    unittest.main()
```


### 3. Фронтенд (Vanilla JS, CSS3, HTML5)

#### Файл: `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube Video Analyzer & Downloader</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="app-header">
    <div class="header-container">
      <div class="logo">
        <span class="logo-icon">▶</span>
        <span class="logo-text">YT Analyzer <span class="badge">Web</span></span>
      </div>
      <div class="server-status" id="serverStatus">
        <span class="status-indicator" id="serverStatusDot"></span>
        <span class="status-text" id="serverStatusText">Проверка сервера...</span>
      </div>
    </div>
  </header>

  <main class="app-main">
    <section class="hero-section">
      <h1 class="hero-title">Анализ и скачивание видео с YouTube</h1>
      <p class="hero-subtitle">Получайте метаданные, превью, транскрипты, видео и аудио MP3/M4A без рекламы и ожидания.</p>

      <form id="analyzeForm" class="search-form">
        <div class="search-box">
          <span class="search-icon">🔗</span>
          <input 
            type="text" 
            id="urlInput" 
            name="url" 
            placeholder="Вставьте ссылку на видео (youtube.com/watch?v=... или youtu.be/...)" 
            required 
            autocomplete="off"
            spellcheck="false"
          >
          <button type="button" id="clearBtn" class="clear-btn hidden" title="Очистить поле">✕</button>
          <button type="button" id="pasteBtn" class="paste-btn" title="Вставить из буфера">
            <span>Вставить</span>
          </button>
        </div>
        <button type="submit" id="submitBtn" class="submit-btn">
          <span class="btn-text">Анализировать</span>
          <div class="spinner hidden" id="submitSpinner"></div>
        </button>
      </form>

      <!-- Alert Box -->
      <div id="alertBox" class="alert-box hidden" role="alert">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
          <h4 id="alertTitle" class="alert-title">Ошибка</h4>
          <p id="alertDesc" class="alert-desc">Описание ошибки</p>
        </div>
        <button type="button" id="alertCloseBtn" class="alert-close">✕</button>
      </div>
    </section>

    <!-- Skeleton Loader -->
    <section id="skeletonLoader" class="skeleton-section hidden">
      <div class="card skeleton-card">
        <div class="skeleton-thumb"></div>
        <div class="skeleton-details">
          <div class="skeleton-line title"></div>
          <div class="skeleton-line meta"></div>
          <div class="skeleton-line desc"></div>
        </div>
      </div>
    </section>

    <!-- Result Section -->
    <section id="resultSection" class="result-section hidden">
      <!-- Video Overview Card -->
      <div class="video-card card">
        <div class="video-preview-wrapper">
          <img id="videoThumb" class="video-thumb" src="" alt="Превью видео">
          <span id="videoDuration" class="duration-badge">00:00</span>
        </div>
        <div class="video-info">
          <h2 id="videoTitle" class="video-title">Название видео</h2>
          
          <div class="metadata-row">
            <div class="meta-item">
              <span class="meta-label">Канал:</span>
              <a id="channelLink" href="#" target="_blank" rel="noopener noreferrer" class="meta-link">
                <span id="channelName">Имя канала</span> ↗
              </a>
            </div>
            <div class="meta-item">
              <span class="meta-label">Опубликовано:</span>
              <span id="uploadDate" class="meta-value">—</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Просмотры:</span>
              <span id="viewCount" class="meta-value">—</span>
            </div>
          </div>

          <div class="video-actions">
            <a id="originalVideoLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
              <span>Смотреть на YouTube</span> ↗
            </a>
            <button type="button" id="copyUrlBtn" class="btn btn-secondary">
              <span>Скопировать ссылку</span>
            </button>
          </div>

          <details class="description-accordion">
            <summary>Описание видео</summary>
            <p id="videoDescription" class="description-text"></p>
          </details>
        </div>
      </div>

      <!-- Download Options Container -->
      <div class="download-tabs card">
        <div class="tabs-header">
          <button type="button" class="tab-btn active" data-tab="videoTab">🎥 Видео (MP4)</button>
          <button type="button" class="tab-btn" data-tab="audioTab">🎵 Аудио (MP3/M4A)</button>
          <button type="button" class="tab-btn" data-tab="subtitlesTab">📝 Субтитры / Текст</button>
          <button type="button" class="tab-btn" data-tab="formatsTab">⚙️ Все потоки</button>
        </div>

        <div class="tabs-content">
          <!-- Video Tab -->
          <div id="videoTab" class="tab-panel active">
            <div class="options-grid" id="videoOptionsGrid">
              <!-- Dynamically populated -->
            </div>
          </div>

          <!-- Audio Tab -->
          <div id="audioTab" class="tab-panel">
            <div class="options-grid" id="audioOptionsGrid">
              <!-- Dynamically populated -->
            </div>
          </div>

          <!-- Subtitles Tab -->
          <div id="subtitlesTab" class="tab-panel">
            <div id="subtitlesContent" class="subtitles-container">
              <!-- Dynamically populated -->
            </div>
          </div>

          <!-- Raw Formats Technical Tab -->
          <div id="formatsTab" class="tab-panel">
            <div class="table-responsive">
              <table class="formats-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Формат</th>
                    <th>Разрешение</th>
                    <th>FPS</th>
                    <th>Размер</th>
                    <th>Видеокодек</th>
                    <th>Аудиокодек</th>
                    <th>Инфо</th>
                  </tr>
                </thead>
                <tbody id="formatsTableBody">
                  <!-- Dynamically populated -->
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- Modal for Transcript preview -->
  <div id="transcriptModal" class="modal hidden">
    <div class="modal-backdrop" id="modalBackdrop"></div>
    <div class="modal-dialog">
      <div class="modal-header">
        <h3 id="modalTitle">Расшифровка субтитров</h3>
        <button type="button" id="modalCloseBtn" class="modal-close">✕</button>
      </div>
      <div class="modal-body">
        <div id="modalLoading" class="modal-loading hidden">
          <div class="spinner"></div>
          <span>Загрузка расшифровки...</span>
        </div>
        <textarea id="modalText" class="modal-textarea" readonly spellcheck="false"></textarea>
      </div>
      <div class="modal-footer">
        <button type="button" id="modalCopyBtn" class="btn btn-secondary">Скопировать в буфер</button>
        <button type="button" id="modalDownloadBtn" class="btn btn-primary">Скачать .txt</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="toast hidden"></div>

  <script src="app.js"></script>
</body>
</html>
```

#### Файл: `frontend/style.css`
```css
/* ==========================================================================
   Modern Dark Theme Design System for YouTube Video Analyzer
   ========================================================================== */

:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --bg-input: #0f172a;
  --card-bg: rgba(30, 41, 59, 0.7);

  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  --accent-red: #ef4444;
  --accent-red-hover: #dc2626;
  --accent-blue: #3b82f6;
  --accent-blue-hover: #2563eb;
  --accent-green: #10b981;
  --accent-yellow: #f59e0b;

  --border-color: rgba(255, 255, 255, 0.08);
  --border-focus: #3b82f6;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;

  --font-main: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.15);
  --shadow-glow: 0 0 25px rgba(59, 130, 246, 0.25);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-main);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  line-height: 1.5;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
}

/* Header */
.app-header {
  border-bottom: 1px solid var(--border-color);
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: -0.02em;
}

.logo-icon {
  color: var(--accent-red);
  font-size: 1.4rem;
  display: inline-flex;
}

.badge {
  font-size: 0.7rem;
  text-transform: uppercase;
  background: var(--bg-tertiary);
  color: var(--accent-blue);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  vertical-align: middle;
}

.server-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--text-muted);
}

.status-indicator.online {
  background: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green);
}

.status-indicator.offline {
  background: var(--accent-red);
}

/* Main */
.app-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
}

/* Hero Section */
.hero-section {
  text-align: center;
  max-width: 780px;
  margin: 0 auto 3rem;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0.75rem;
  background: linear-gradient(to right, #f8fafc, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
  margin-bottom: 2rem;
}

/* Search Form */
.search-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: var(--bg-secondary);
  padding: 0.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);
  transition: all 0.2s ease;
}

.search-form:focus-within {
  border-color: var(--border-focus);
  box-shadow: var(--shadow-glow);
}

.search-box {
  display: flex;
  align-items: center;
  position: relative;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 0 0.75rem;
}

.search-icon {
  font-size: 1.1rem;
  margin-right: 0.5rem;
  color: var(--text-muted);
}

.search-box input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1rem;
  padding: 0.85rem 0.5rem;
  outline: none;
}

.search-box input::placeholder {
  color: var(--text-muted);
}

.clear-btn, .paste-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  transition: all 0.15s ease;
}

.clear-btn:hover, .paste-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.submit-btn {
  background: var(--accent-red);
  color: #fff;
  border: none;
  font-weight: 600;
  font-size: 1rem;
  padding: 0.85rem 1.5rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: background 0.15s ease, transform 0.1s ease;
}

.submit-btn:hover {
  background: var(--accent-red-hover);
}

.submit-btn:active {
  transform: scale(0.98);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Alert Box */
.alert-box {
  margin-top: 1.5rem;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  text-align: left;
}

.alert-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--accent-red);
  margin-bottom: 0.2rem;
}

.alert-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.alert-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  margin-left: auto;
}

/* Card */
.card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(8px);
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
}

/* Video Card */
.video-card {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

.video-preview-wrapper {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 16 / 9;
  background: #000;
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.8);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.video-info {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 1rem;
}

.video-title {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.3;
}

.metadata-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  font-size: 0.9rem;
}

.meta-label {
  color: var(--text-muted);
  margin-right: 0.3rem;
}

.meta-link {
  color: var(--accent-blue);
  text-decoration: none;
  font-weight: 500;
}

.meta-link:hover {
  text-decoration: underline;
}

.video-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 0.6rem 1rem;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--accent-blue);
  color: #fff;
}

.btn-primary:hover {
  background: var(--accent-blue-hover);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: #475569;
}

.description-accordion {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  border-top: 1px solid var(--border-color);
  padding-top: 0.75rem;
}

.description-accordion summary {
  cursor: pointer;
  color: var(--text-muted);
  user-select: none;
}

.description-accordion summary:hover {
  color: var(--text-secondary);
}

.description-text {
  margin-top: 0.5rem;
  color: var(--text-secondary);
  white-space: pre-wrap;
  max-height: 180px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  line-height: 1.6;
}

/* Download Tabs */
.tabs-header {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.75rem;
  margin-bottom: 1.5rem;
  overflow-x: auto;
}

.tab-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.95rem;
  font-weight: 600;
  padding: 0.6rem 1.1rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.tab-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.tab-btn.active {
  color: #fff;
  background: var(--accent-blue);
}

.tab-panel {
  display: none;
}

.tab-panel.active {
  display: block;
}

/* Options Grid */
.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.option-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.2rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  transition: all 0.15s ease;
}

.option-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.option-badge {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--accent-blue);
}

.option-size {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.option-title {
  font-size: 1rem;
  font-weight: 600;
}

.download-stream-btn {
  width: 100%;
  background: var(--accent-blue);
  color: #fff;
  border: none;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0.65rem 1rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: background 0.15s ease;
}

.download-stream-btn:hover {
  background: var(--accent-blue-hover);
}

.download-stream-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

/* Subtitles Grid */
.subtitles-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.subtitle-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 0.85rem 1.25rem;
  border-radius: var(--radius-md);
}

.subtitle-lang-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.subtitle-actions {
  display: flex;
  gap: 0.5rem;
}

/* Raw Formats Table */
.table-responsive {
  overflow-x: auto;
}

.formats-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.formats-table th {
  background: var(--bg-tertiary);
  padding: 0.65rem 0.75rem;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.formats-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.formats-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-primary);
}

/* Modal */
.modal {
  position: fixed;
  inset: 0;
  z-index: 200;
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

.modal-dialog {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 680px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  z-index: 210;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 1.15rem;
  font-weight: 700;
}

.modal-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.2rem;
}

.modal-body {
  padding: 1.25rem 1.5rem;
  overflow-y: auto;
  flex: 1;
  position: relative;
}

.modal-textarea {
  width: 100%;
  height: 320px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  padding: 0.75rem;
  resize: none;
  line-height: 1.5;
  outline: none;
}

.modal-loading {
  position: absolute;
  inset: 0;
  background: rgba(30, 41, 59, 0.9);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
  justify-content: center;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

/* Spinner */
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Skeleton Loading */
.skeleton-card {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

.skeleton-thumb {
  aspect-ratio: 16 / 9;
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-line {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
  margin-bottom: 0.75rem;
}

.skeleton-line.title {
  height: 28px;
  width: 70%;
}

.skeleton-line.meta {
  height: 16px;
  width: 40%;
}

.skeleton-line.desc {
  height: 80px;
  width: 100%;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--accent-blue);
  box-shadow: var(--shadow-lg);
  padding: 0.85rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 500;
  z-index: 300;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.hidden {
  display: none !important;
}

/* Responsive */
@media (max-width: 860px) {
  .video-card, .skeleton-card {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }

  .hero-title {
    font-size: 1.85rem;
  }
}
```

#### Файл: `frontend/app.js`
```javascript
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
 * 1. Health check & Keep-Alive Initializer (Render Free Spin-Down Guard)
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
  // Periodic health check every 4 minutes while tab is open to prevent Render Free spin-down
  setInterval(checkHealth, 240000);
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
    } catch (err) {
      showToast("Не удалось прочитать буфер обмена");
    }
  });

  // Alert close
  alertCloseBtn.addEventListener("click", hideAlert);

  // Form submission
  analyzeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    await performAnalysis(url);
  });

  // Tabs switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    });
  });

  // Modal actions
  modalCloseBtn.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !transcriptModal.classList.contains("hidden")) {
      closeModal();
    }
  });

  modalCopyBtn.addEventListener("click", () => {
    if (currentTranscriptText) {
      navigator.clipboard.writeText(currentTranscriptText);
      showToast("Текст расшифровки скопирован в буфер обмена!");
    }
  });

  // Copy video URL button
  copyUrlBtn.addEventListener("click", () => {
    if (currentVideoData && currentVideoData.original_url) {
      navigator.clipboard.writeText(currentVideoData.original_url);
      showToast("Ссылка на видео скопирована в буфер!");
    }
  });
}

/* -------------------------------------------------------------
 * 3. Main Video Analysis
 * ------------------------------------------------------------- */
async function performAnalysis(url) {
  hideAlert();
  setLoading(true);
  resultSection.classList.add("hidden");
  skeletonLoader.classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      let errorMsg = "Не удалось проанализировать видео";
      try {
        const errorData = await res.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (e) {
        errorMsg = `Ошибка сервера (${res.status} ${res.statusText})`;
      }
      showAlert("Ошибка анализа", errorMsg);
      return;
    }

    const data = await res.json();
    currentVideoData = data;
    renderResults(data);
    checkHealth();
  } catch (err) {
    showAlert("Ошибка сети", `Не удалось связаться с сервером: ${err.message}`);
  } finally {
    setLoading(false);
    skeletonLoader.classList.add("hidden");
  }
}

/* -------------------------------------------------------------
 * 4. Render UI Components
 * ------------------------------------------------------------- */
function renderResults(data) {
  // Populate video details
  videoThumb.src = data.thumbnail || "";
  videoThumb.alt = data.title;
  videoDuration.textContent = data.duration_str;
  videoTitle.textContent = data.title;

  channelName.textContent = data.channel;
  if (data.channel_url) {
    channelLink.href = data.channel_url;
    channelLink.classList.remove("hidden");
  } else {
    channelLink.classList.add("hidden");
  }

  uploadDate.textContent = data.upload_date || "Не указана";
  viewCount.textContent =
    data.view_count !== null && data.view_count !== undefined
      ? data.view_count.toLocaleString("ru-RU")
      : "Скрыто";
  originalVideoLink.href = data.original_url;
  videoDescription.textContent = data.description || "Описание отсутствует.";

  // Render tabs
  renderVideoOptions(data.video_options);
  renderAudioOptions(data.audio_options);
  renderSubtitles(data.subtitle_options);
  renderFormatsTable(data.all_formats);

  // Reveal result
  resultSection.classList.remove("hidden");
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderVideoOptions(options) {
  videoOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    videoOptionsGrid.innerHTML = "<p class='text-muted'>Доступные видеопотоки не найдены.</p>";
    return;
  }

  options.forEach((opt) => {
    const isAvailable = opt.available !== false;
    const card = document.createElement("div");
    card.className = "option-card";
    card.innerHTML = `
      <div class="option-header">
        <span class="option-badge">${escapeHtml(opt.quality)}</span>
        <span class="option-size">${isAvailable ? "~" : ""}${escapeHtml(opt.filesize_str)}</span>
      </div>
      <div class="option-title">${escapeHtml(opt.label)}</div>
      <button type="button" class="download-stream-btn" data-url="${escapeHtml(opt.download_url)}" ${!isAvailable ? "disabled" : ""}>
        <span>${isAvailable ? "Скачать MP4" : "Недоступно"}</span>
      </button>
    `;

    if (isAvailable) {
      card.querySelector(".download-stream-btn").addEventListener("click", function () {
        triggerDownload(this, opt.download_url);
      });
    }

    videoOptionsGrid.appendChild(card);
  });
}

function renderAudioOptions(options) {
  audioOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    audioOptionsGrid.innerHTML = "<p class='text-muted'>Доступные аудиопотоки не найдены.</p>";
    return;
  }

  options.forEach((opt) => {
    const isAvailable = opt.available !== false;
    const card = document.createElement("div");
    card.className = "option-card";
    card.innerHTML = `
      <div class="option-header">
        <span class="option-badge">${escapeHtml(opt.format.toUpperCase())}</span>
        <span class="option-size">~${escapeHtml(opt.filesize_str)}</span>
      </div>
      <div class="option-title">${escapeHtml(opt.label)}</div>
      <button type="button" class="download-stream-btn" data-url="${escapeHtml(opt.download_url)}" ${!isAvailable ? "disabled" : ""}>
        <span>${isAvailable ? "Скачать " + escapeHtml(opt.format.toUpperCase()) : "Требуется FFmpeg"}</span>
      </button>
    `;

    if (isAvailable) {
      card.querySelector(".download-stream-btn").addEventListener("click", function () {
        triggerDownload(this, opt.download_url);
      });
    }

    audioOptionsGrid.appendChild(card);
  });
}

function renderSubtitles(subtitles) {
  subtitlesContent.innerHTML = "";
  if (!subtitles || subtitles.length === 0) {
    subtitlesContent.innerHTML = `
      <div class="alert-box" style="margin-top:0;">
        <span class="alert-icon">ℹ️</span>
        <div class="alert-content">
          <p class="alert-desc">Для данного видео не найдено ручных или автоматически сгенерированных субтитров.</p>
        </div>
      </div>
    `;
    return;
  }

  subtitles.forEach((sub) => {
    const item = document.createElement("div");
    item.className = "subtitle-item";
    item.innerHTML = `
      <div class="subtitle-lang-info">
        <span class="option-badge">${escapeHtml(sub.lang)}</span>
        <span><strong>${escapeHtml(sub.name)}</strong></span>
      </div>
      <div class="subtitle-actions">
        <button type="button" class="btn btn-secondary preview-sub-btn">
          <span>Предпросмотр</span>
        </button>
        <button type="button" class="btn btn-primary download-txt-btn">
          <span>Скачать .txt</span>
        </button>
        <button type="button" class="btn btn-secondary download-srt-btn">
          <span>Скачать .srt</span>
        </button>
      </div>
    `;

    item.querySelector(".preview-sub-btn").addEventListener("click", () => {
      openTranscriptModal(sub);
    });

    item.querySelector(".download-txt-btn").addEventListener("click", function () {
      triggerDownload(this, sub.txt_url);
    });

    item.querySelector(".download-srt-btn").addEventListener("click", function () {
      triggerDownload(this, sub.srt_url);
    });

    subtitlesContent.appendChild(item);
  });
}

function renderFormatsTable(formats) {
  formatsTableBody.innerHTML = "";
  if (!formats || formats.length === 0) {
    formatsTableBody.innerHTML = "<tr><td colspan='8'>Информация о форматах отсутствует</td></tr>";
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
        const ext =
          kind === "audio"
            ? format || "mp3"
            : kind === "transcript"
              ? lang
                ? `${lang}.${format || "txt"}`
                : format || "txt"
              : "mp4";
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
  modalText.value = "";
  modalLoading.classList.remove("hidden");
  currentTranscriptText = "";

  try {
    const res = await fetch(subOption.txt_url);
    if (!res.ok) {
      let detail = "Не удалось загрузить текст субтитров";
      try {
        const errData = await res.json();
        detail = errData.detail || detail;
      } catch (e) {
        detail = `Ошибка сервера (${res.status})`;
      }
      throw new Error(detail);
    }
    const text = await res.text();
    currentTranscriptText = text;
    modalText.value = text || "(Субтитры пусты)";
  } catch (err) {
    modalText.value = `Ошибка: ${err.message}`;
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
```


### 4. Документация проекта

#### Файл: `README.md`
```markdown
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
