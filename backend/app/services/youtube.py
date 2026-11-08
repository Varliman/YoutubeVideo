"""YouTube extraction and media downloading service using yt-dlp and ffmpeg."""

import os
import re
import json
import html
import time
import uuid
import shutil
import logging
import threading
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
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

HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


def sanitize_error_message(error: Exception | str) -> str:
    """Strips passwords and sensitive credentials from error messages and proxy URLs."""
    msg = str(error)
    msg = re.sub(r'\x1b\[[0-9;]*m', '', msg)
    msg = re.sub(r'://([^:/\s]+):([^@/\s]+)@', r'://\1:***@', msg)
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
_pot_server_proc: Optional[subprocess.Popen] = None

# 180-second in-memory metadata cache to prevent redundant extract_info calls
_INFO_CACHE: dict[str, Tuple[float, dict]] = {}
_INFO_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 180.0
_MAX_CACHE_ENTRIES = 64

# Prepared files registry for two-phase download (token -> (file_path, filename, mime_type, timestamp))
_PREPARED_FILES: dict[str, Tuple[Path, str, str, float]] = {}
_PREPARED_FILES_LOCK = threading.Lock()
_PREPARED_TTL_SECONDS = 600.0  # 10 minutes


def start_pot_provider_daemon():
    """
    Starts the lightweight Rust bgutil-pot HTTP server on 127.0.0.1:4416 if installed.
    Provides automatic BotGuard PO Tokens to yt-dlp to bypass YouTube datacenter IP blocks.
    """
    global _pot_server_proc
    pot_bin = shutil.which("bgutil-pot")
    if not pot_bin:
        return
    if _pot_server_proc and _pot_server_proc.poll() is None:
        return
    try:
        _pot_server_proc = subprocess.Popen(
            [pot_bin, "server", "--host", "127.0.0.1", "--port", "4416"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Started bgutil-pot PO Token server on 127.0.0.1:4416")
    except Exception as e:
        logger.warning(f"Could not start bgutil-pot server: {e}")


def register_prepared_file(file_path: Path, filename: str, mime_type: str) -> str:
    """Registers a downloaded file for immediate streaming via /api/stream/{token}."""
    now = time.time()
    token = uuid.uuid4().hex
    with _PREPARED_FILES_LOCK:
        expired = [k for k, (_, _, _, ts) in _PREPARED_FILES.items() if now - ts > _PREPARED_TTL_SECONDS]
        for k in expired:
            old_entry = _PREPARED_FILES.pop(k, None)
            if old_entry:
                shutil.rmtree(old_entry[0].parent, ignore_errors=True)
        _PREPARED_FILES[token] = (file_path, filename, mime_type, now)
    return token


def pop_prepared_file(token: str) -> Optional[Tuple[Path, str, str]]:
    """Retrieves and removes a prepared file token so it can be streamed and cleaned up."""
    with _PREPARED_FILES_LOCK:
        entry = _PREPARED_FILES.pop(token, None)
    if not entry:
        return None
    file_path, filename, mime_type, _ = entry
    if not file_path.exists():
        return None
    return file_path, filename, mime_type


def _is_storyboard_or_non_media(f: dict) -> bool:
    """Returns True if a format dictionary is merely a storyboard image sheet rather than audio/video."""
    ext = (f.get("ext") or "").lower()
    protocol = (f.get("protocol") or "").lower()
    note = (f.get("format_note") or "").lower()
    if ext == "mhtml" or protocol == "mhtml" or "storyboard" in note:
        return True
    vcodec = f.get("vcodec")
    acodec = f.get("acodec")
    if vcodec == "none" and acodec == "none":
        return True
    return False


def _has_playable_formats(info: Optional[dict]) -> bool:
    """Checks whether extracted info contains at least one playable video or audio stream."""
    if not info:
        return False
    formats = info.get("formats") or []
    return any(not _is_storyboard_or_non_media(f) for f in formats)


# Client fallback profiles for yt-dlp 2026+ (avoiding broken 'tv' client that causes 'The page needs to be reloaded')
_CLIENT_PROFILES: list[dict] = [
    # Profile 1: Default clients + web_embedded + mweb + android_vr with Node.js EJS solver
    {
        "player_client": ["default", "web_embedded", "mweb", "android_vr"],
    },
    # Profile 2: Enable formats=missing_pot so yt-dlp does NOT skip streams when PO Token is absent on datacenter IPs
    {
        "player_client": ["default", "ios", "mweb", "android_vr", "web_embedded"],
        "formats": ["missing_pot"],
    },
    # Profile 3: Mobile/VR clients with missing_pot + duplicate formats unlocked
    {
        "player_client": ["android_vr", "mweb", "ios", "web_safari"],
        "formats": ["missing_pot", "duplicate"],
    },
]


def _extract_with_client_fallbacks(url: str, base_extra_opts: dict, download: bool = False) -> dict:
    """
    Executes yt-dlp extract_info with automatic fallback across client profiles.
    If download=False (metadata/analyze mode) and all profiles fail to unlock playable streams,
    falls back to ignore_no_formats_error=True so metadata and subtitles still work.
    """
    last_exc = None
    for idx, youtube_args in enumerate(_CLIENT_PROFILES):
        extra = dict(base_extra_opts)
        extra["extractor_args"] = {"youtube": dict(youtube_args)}
        opts = get_ydl_base_opts(extra)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
                if download or _has_playable_formats(info) or (info and info.get("formats")):
                    return info
        except Exception as e:
            last_exc = e
            err_str = str(e)
            logger.warning(f"yt-dlp attempt {idx + 1} failed for {url}: {sanitize_error_message(e)}")
            if "Private video" in err_str or "Video unavailable" in err_str or "File is larger than max-filesize" in err_str:
                raise e
            continue

    # If we are only extracting metadata (e.g. /api/analyze or subtitles) and formats were blocked,
    # extract with ignore_no_formats_error=True so video info & transcripts remain accessible!
    if not download:
        try:
            fallback_extra = dict(base_extra_opts)
            fallback_extra["ignore_no_formats_error"] = True
            fallback_extra["extractor_args"] = {
                "youtube": {
                    "player_client": ["default", "web_embedded", "mweb", "ios"],
                    "formats": ["missing_pot"],
                }
            }
            opts = get_ydl_base_opts(fallback_extra)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return info
        except Exception as e:
            last_exc = e

    if last_exc:
        raise last_exc
    raise yt_dlp.utils.DownloadError("Не удалось получить данные о видеопотоках YouTube.")


def get_cached_or_extract_info(url: str, extra_opts: Optional[dict] = None) -> dict:
    """
    Retrieves video info dictionary from in-memory cache or extracts via yt-dlp.
    Cached for 180 seconds to eliminate redundant network extraction between analyze, pre-check, and download.
    """
    now = time.time()
    with _INFO_CACHE_LOCK:
        expired = [k for k, (ts, _) in _INFO_CACHE.items() if now - ts > 300]
        for k in expired:
            _INFO_CACHE.pop(k, None)

        cached = _INFO_CACHE.get(url)
        if cached and (now - cached[0] < _CACHE_TTL_SECONDS):
            return cached[1]

    req_opts = {
        "skip_download": True,
        "retries": 3,
        "extractor_retries": 3,
    }
    if extra_opts:
        req_opts.update(extra_opts)

    info = _extract_with_client_fallbacks(url, req_opts, download=False)

    with _INFO_CACHE_LOCK:
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
    3. Checks format/quality availability (verifies playable video height <= requested quality).
    Returns: (is_ok: bool, message: str, title: Optional[str])
    """
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

    try:
        info = get_cached_or_extract_info(url)
    except yt_dlp.utils.DownloadError as e:
        err_msg = sanitize_error_message(e)
        if "429" in err_msg:
            return False, "YouTube заблокировал IP-адрес сервера (HTTP 429 Too Many Requests).", None
        elif "Private video" in err_msg or "Sign in" in err_msg or "not a bot" in err_msg:
            return False, "Видео требует авторизации YouTube (приватное, 18+ или проверка бота). Добавьте COOKIES_TEXT или PROXY_URL.", None
        elif "Video unavailable" in err_msg:
            return False, "Видео недоступно, удалено или заблокировано правообладателем.", None
        return False, f"Ошибка доступа к видео: {err_msg}", None
    except Exception as e:
        return False, f"Ошибка проверки видео: {sanitize_error_message(e)}", None

    title = info.get("title", "")

    if info.get("is_live"):
        return False, "Это видео является прямым эфиром (Live stream). Скачивание станет доступно после завершения трансляции.", title
    if info.get("live_status") == "is_upcoming":
        return False, "Это видео является запланированной премьерой. Скачивание пока недоступно.", title

    duration = info.get("duration") or 0
    if duration > settings.MAX_DURATION_SECONDS:
        max_hours = settings.MAX_DURATION_SECONDS // 3600
        return (
            False,
            f"Длительность видео ({format_duration(duration)}) превышает допустимый лимит сервера ({max_hours} ч).",
            title,
        )

    if kind == "video" and quality:
        cap = settings.MAX_VIDEO_HEIGHT or 1080
        quality_map = {"best": cap, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
        target_h = quality_map.get(quality, cap)
        want = min(target_h, cap)
        formats = [f for f in (info.get("formats") or []) if not _is_storyboard_or_non_media(f)]
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

    steps = [h for h in (1080, 720, 480, 360) if h <= target_h]
    parts = []
    for h in steps:
        parts.append(f"bestvideo[height<={h}][vcodec^=avc]+bestaudio[ext=m4a]")
        parts.append(f"bestvideo[height<={h}]+bestaudio")
        parts.append(f"best[height<={h}]")
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


def get_nodejs_available() -> bool:
    """Checks if Node.js or Deno is installed in PATH for yt-dlp-ejs signature solving."""
    return bool(shutil.which("node") or shutil.which("nodejs") or shutil.which("deno"))


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
    read-only (e.g. Render Secret Files at /etc/secrets/cookies.txt or Docker :ro volumes).
    """
    runtime_cookies = settings.STORAGE_DIR / "runtime_cookies.txt"

    with _cookies_lock:
        if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
            try:
                src_path = Path(settings.COOKIES_FILE).resolve()
                if src_path != runtime_cookies.resolve():
                    if not runtime_cookies.exists() or src_path.stat().st_mtime > runtime_cookies.stat().st_mtime:
                        shutil.copyfile(src_path, runtime_cookies)
                return str(runtime_cookies)
            except Exception as e:
                logger.warning(f"Could not copy COOKIES_FILE to writable storage: {e}")
                return settings.COOKIES_FILE

        elif settings.COOKIES_TEXT:
            try:
                raw_text = settings.COOKIES_TEXT.strip()
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
    """
    Constructs base yt-dlp options including explicit Node.js runtime activation
    (CRITICAL for yt-dlp 2026+ which only enables deno by default!), proxy, cookies,
    single-thread FFmpeg, and timeouts.
    """
    # Configure JS runtimes explicitly: yt-dlp 2026+ only checks deno by default unless node is passed!
    js_runtimes = {}
    node_bin = shutil.which("node") or shutil.which("nodejs")
    if node_bin:
        js_runtimes["node"] = {"path": node_bin}
    else:
        js_runtimes["node"] = {}
    deno_bin = shutil.which("deno")
    if deno_bin:
        js_runtimes["deno"] = {"path": deno_bin}

    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "geo_bypass": True,
        "js_runtimes": js_runtimes,
        "socket_timeout": settings.YTDLP_TIMEOUT_SECONDS,
        "retries": 5,
        "fragment_retries": 5,
        "continuedl": True,
        "nopart": True,
        "http_chunk_size": 10485760,
        "postprocessor_args": {
            "ffmpeg": ["-threads", "1"],
        },
    }

    if getattr(settings, "FORCE_IPV4", True):
        opts["source_address"] = "0.0.0.0"

    if settings.PROXY_URL:
        opts["proxy"] = settings.PROXY_URL

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
    lower_msg = error_msg.lower()
    if "429" in error_msg or "too many requests" in lower_msg:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "YouTube временно ограничил запросы с IP-адреса сервера (HTTP 429 Too Many Requests). "
                "Для стабильной работы на облачном хостинге Render укажите COOKIES_TEXT или PROXY_URL в Environment Variables."
            )
        )
    elif (
        "private video" in lower_msg
        or "sign in" in lower_msg
        or "not a bot" in lower_msg
        or "age-restricted" in lower_msg
        or "http error 403" in lower_msg
        or "the page needs to be reloaded" in lower_msg
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "YouTube запросил проверку авторизации или защиту от ботов (HTTP 403 / 'Sign in to confirm you’re not a bot') "
                "для IP-адреса датацентра Render. Чтобы скачивать любые видео без ограничений, добавьте переменную "
                "COOKIES_TEXT (содержимое файла cookies.txt из браузера) или PROXY_URL в настройках Environment на Render."
            )
        )
    elif "requested format is not available" in lower_msg:
        raise HTTPException(
            status_code=HTTP_422_STATUS,
            detail=(
                f"Видеопоток в выбранном качестве (лимит ≤{settings.MAX_VIDEO_HEIGHT}p) недоступен. "
                "YouTube заблокировал отдачу прямых видеопотоков для IP-адреса датацентра Render — "
                "добавьте COOKIES_TEXT (куки из браузера) или PROXY_URL в настройки Environment на Render."
            )
        )
    elif "file is larger than max-filesize" in lower_msg:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер видеопотока превышает допустимый лимит сервера ({settings.MAX_FILE_SIZE_MB} МБ)."
        )
    elif "video unavailable" in lower_msg:
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

    all_formats: list[FormatItem] = []
    raw_formats = meta.get("formats", [])
    formats = [f for f in raw_formats if not _is_storyboard_or_non_media(f)]

    if not formats and not (meta.get("subtitles") or meta.get("automatic_captions")):
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
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "YouTube не отдал медиапотоки для IP-адреса сервера (возвращены только превью-раскадровки). "
                    "Для обхода ограничения датацентра Render укажите COOKIES_TEXT или PROXY_URL в Environment Variables."
                )
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

    audio_est_bytes = duration * (160 * 1024 / 8) if duration > 0 else 0
    encoded_url = urllib.parse.quote(url, safe="")
    has_any_media_formats = len(formats) > 0

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
        effective_cap = max_h or server_cap
        has_compatible_stream = has_any_media_formats and (
            (not available_heights) or any(0 < h <= effective_cap for h in available_heights)
        )
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
            available=bool(ffmpeg_ok and has_any_media_formats),
        ),
        AudioOption(
            format="m4a",
            label="Аудио M4A (Оригинальный AAC-поток YouTube)",
            bitrate_kbps=128,
            filesize_approx_mb=round(m4a_bytes / (1024 * 1024), 1) if m4a_bytes else None,
            filesize_str=format_bytes(m4a_bytes) if m4a_bytes else "Размер уточняется",
            download_url=f"/api/download/audio?url={encoded_url}&format=m4a",
            available=has_any_media_formats,
        ),
    ]

    subtitle_options: list[SubtitleOption] = []
    seen_langs = set()

    manual_subs = meta.get("subtitles") or {}
    for lang, track_list in manual_subs.items():
        if lang == "live_chat" or not track_list:
            continue
        name = track_list[0].get("name", lang) if isinstance(track_list[0], dict) else lang
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

    auto_subs = meta.get("automatic_captions") or {}
    for lang, track_list in auto_subs.items():
        if lang not in seen_langs and lang != "live_chat" and track_list:
            name = track_list[0].get("name", lang) if isinstance(track_list[0], dict) else lang
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
    Includes automatic client fallback if YouTube blocks a specific player client.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
    if settings.MAX_VIDEO_HEIGHT and quality == "1080p" and settings.MAX_VIDEO_HEIGHT < 1080:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Качество 1080p отключено из-за ограничения памяти сервера (512 МБ RAM). "
                f"Максимальное допустимое разрешение: {settings.MAX_VIDEO_HEIGHT}p."
            )
        )

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

        dl_opts = {
            "format": fmt,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
            "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        }

        try:
            info = _extract_with_client_fallbacks(url, dl_opts, download=True)
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

        downloaded_height = info.get("height") or 0
        if settings.MAX_VIDEO_HEIGHT and downloaded_height > settings.MAX_VIDEO_HEIGHT + 1:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=HTTP_422_STATUS,
                detail=f"Скачанное разрешение ({downloaded_height}p) превышает лимит сервера ({settings.MAX_VIDEO_HEIGHT}p)."
            )

        downloaded_files = [f for f in job_dir.glob("*.mp4") if f.is_file()]
        if not downloaded_files:
            downloaded_files = [f for f in job_dir.iterdir() if f.is_file() and f.suffix.lower() not in (".part", ".ytdl")]

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
            dl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": out_template,
                "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }],
            }
            expected_ext = ".mp3"
            mime_type = "audio/mpeg"
        else:  # m4a
            dl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": out_template,
                "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
            }
            expected_ext = ".m4a"
            mime_type = "audio/mp4"

        try:
            info = _extract_with_client_fallbacks(url, dl_opts, download=True)
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

        downloaded_files = [f for f in job_dir.glob(f"*{expected_ext}") if f.is_file()]
        if not downloaded_files:
            downloaded_files = [f for f in job_dir.iterdir() if f.is_file() and f.suffix.lower() not in (".part", ".ytdl")]

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


def _ms_to_srt_timestamp(ms: int | float) -> str:
    """Formats milliseconds into SubRip timestamp HH:MM:SS,mmm."""
    total_ms = max(0, int(ms))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    seconds = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _parse_json3_or_xml_to_vtt_or_srt(raw_content: str) -> Optional[str]:
    """
    If raw_content is YouTube JSON3 ({"events": [...]}) or XML/SRV1/SRV2/SRV3/TTML (<transcript>/<timedtext>),
    converts it into standard SRT blocks. Returns None if content is already VTT/SRT text.
    """
    stripped = raw_content.lstrip()
    if not stripped:
        return None

    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            events = data.get("events") or []
            blocks = []
            for ev in events:
                segs = ev.get("segs")
                if not segs:
                    continue
                text = "".join(s.get("utf8", "") for s in segs).strip()
                text = re.sub(r"\s+", " ", text).strip()
                if not text:
                    continue
                start_ms = ev.get("tStartMs", 0)
                dur_ms = ev.get("dDurationMs", 3000)
                ts = f"{_ms_to_srt_timestamp(start_ms)} --> {_ms_to_srt_timestamp(start_ms + dur_ms)}"
                if not blocks or blocks[-1][1] != text:
                    blocks.append((ts, text))
            if blocks:
                return "\n\n".join(f"{i}\n{ts}\n{txt}" for i, (ts, txt) in enumerate(blocks, 1))
        except Exception:
            pass

    if stripped.startswith("<"):
        try:
            root = ET.fromstring(stripped)
            blocks = []
            for elem in root.iter():
                tag = elem.tag.split("}")[-1].lower()
                if tag in ("text", "p", "s"):
                    raw_txt = "".join(elem.itertext()).strip()
                    clean_txt = html.unescape(re.sub(r"<[^>]+>", "", raw_txt)).strip()
                    clean_txt = re.sub(r"\s+", " ", clean_txt)
                    if not clean_txt:
                        continue
                    start_ms = 0
                    dur_ms = 3000
                    if "t" in elem.attrib:
                        start_ms = int(float(elem.attrib["t"]))
                        dur_ms = int(float(elem.attrib.get("d", 3000)))
                    elif "start" in elem.attrib:
                        start_ms = int(float(elem.attrib["start"]) * 1000)
                        dur_ms = int(float(elem.attrib.get("dur", 3.0)) * 1000)
                    ts = f"{_ms_to_srt_timestamp(start_ms)} --> {_ms_to_srt_timestamp(start_ms + dur_ms)}"
                    if not blocks or blocks[-1][1] != clean_txt:
                        blocks.append((ts, clean_txt))
            if blocks:
                return "\n\n".join(f"{i}\n{ts}\n{txt}" for i, (ts, txt) in enumerate(blocks, 1))
        except Exception:
            pass

    return None


def vtt_to_srt(vtt_content: str) -> str:
    """
    Pure-Python converter from WebVTT (.vtt), JSON3, or SRV XML to standard SubRip (.srt).
    Avoids spawning an FFmpeg child process on Render Free 512MB RAM.
    """
    converted_structured = _parse_json3_or_xml_to_vtt_or_srt(vtt_content)
    if converted_structured:
        return converted_structured

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

        if (
            line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("Style:")
            or line.startswith("NOTE")
        ):
            continue

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
    Cleans an SRT, WebVTT, JSON3, or SRV XML string into pure legible text:
    removes WEBVTT headers, numeric indexes, timestamps, HTML tags, entities,
    and duplicate consecutive lines.
    """
    converted_structured = _parse_json3_or_xml_to_vtt_or_srt(srt_content)
    if converted_structured:
        srt_content = converted_structured

    lines = []
    prev_line = ""
    for raw_line in srt_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if (
            line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("Style:")
            or line.startswith("NOTE")
        ):
            continue
        if re.match(r"^\d+$", line):
            continue
        if "-->" in line or re.match(r"^\d{2}:\d{2}(:\d{2})?[.,]\d{3}", line):
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        clean = html.unescape(clean).strip()
        if clean and clean != prev_line:
            lines.append(clean)
            prev_line = clean

    return "\n".join(lines)


def _fetch_subtitle_from_info_tracks(info: dict, lang: str) -> Optional[str]:
    """
    Directly downloads subtitle content using the track URLs already extracted in `info`
    (from `subtitles` or `automatic_captions`).
    """
    manual_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    track_list = None
    if lang in manual_subs and manual_subs[lang]:
        track_list = manual_subs[lang]
    elif lang in auto_subs and auto_subs[lang]:
        track_list = auto_subs[lang]
    else:
        for d in (manual_subs, auto_subs):
            for k, v in d.items():
                if (k.startswith(f"{lang}-") or k.startswith(f"{lang}_")) and v:
                    track_list = v
                    break
            if track_list:
                break

    if not track_list and lang in ("ru", "en"):
        for fallback_k in ("ru", "en"):
            if fallback_k in manual_subs and manual_subs[fallback_k]:
                track_list = manual_subs[fallback_k]
                break
            if fallback_k in auto_subs and auto_subs[fallback_k]:
                track_list = auto_subs[fallback_k]
                break

    if not track_list or not isinstance(track_list, list):
        return None

    ext_priority = {"srt": 0, "vtt": 1, "json3": 2, "srv3": 3, "srv2": 4, "srv1": 5, "ttml": 6}
    sorted_tracks = sorted(
        [t for t in track_list if isinstance(t, dict) and t.get("url")],
        key=lambda t: ext_priority.get((t.get("ext") or "").lower(), 99)
    )

    if not sorted_tracks:
        return None

    opts = get_ydl_base_opts({"skip_download": True})
    with yt_dlp.YoutubeDL(opts) as ydl:
        for track in sorted_tracks[:3]:
            sub_url = track["url"]
            try:
                resp = ydl.urlopen(sub_url)
                raw_bytes = resp.read()
                text = raw_bytes.decode("utf-8", errors="replace").strip()
                if text:
                    return text
            except Exception as e:
                logger.warning(f"Direct subtitle track fetch failed ({track.get('ext')}): {sanitize_error_message(e)}")
                continue

    return None


def _find_matching_sub_file(job_dir: Path, target_lang: str) -> Optional[Path]:
    """Finds downloaded subtitle file matching target_lang first, then any subtitle file candidate."""
    sub_exts = (".srt", ".vtt", ".json3", ".srv3", ".srv2", ".srv1", ".ttml")
    for ext in sub_exts:
        matches = list(job_dir.glob(f"*.{target_lang}{ext}"))
        if matches:
            return matches[0]
    for ext in sub_exts:
        matches = list(job_dir.glob(f"*{ext}"))
        if matches:
            return matches[0]
    return None


def download_subtitles_file(url: str, lang: str = "ru", format_type: str = "txt") -> Tuple[Path, str, str]:
    """
    Extracts subtitles (first directly from cached info track URLs, then via yt-dlp fallback).
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

        title = "subtitles"
        content: Optional[str] = None

        try:
            info = get_cached_or_extract_info(url)
            if info and info.get("title"):
                title = sanitize_filename(info.get("title", "transcript"))
            content = _fetch_subtitle_from_info_tracks(info, lang)
        except Exception as e:
            logger.warning(f"Cached info subtitle extraction failed: {sanitize_error_message(e)}")

        if not content:
            out_template = str(job_dir / "subtitles.%(ext)s")
            for is_auto in (False, True):
                ydl_opts_sub = get_ydl_base_opts({
                    "skip_download": True,
                    "ignore_no_formats_error": True,
                    "writesubtitles": not is_auto,
                    "writeautomaticsub": is_auto,
                    "subtitleslangs": [lang],
                    "subtitlesformat": "srt/vtt/best",
                    "outtmpl": out_template,
                })
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_sub) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info and info.get("title"):
                            title = sanitize_filename(info.get("title", "transcript"))
                except Exception as e:
                    logger.warning(f"Error checking subs (auto={is_auto}) [{lang}]: {sanitize_error_message(e)}")

                found_sub = _find_matching_sub_file(job_dir, lang)
                if found_sub:
                    try:
                        content = found_sub.read_text(encoding="utf-8", errors="replace")
                        break
                    except Exception:
                        pass

        if not content or not content.strip():
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Субтитры для языка '{lang}' не найдены или YouTube временно ограничил отдачу субтитров "
                    "для IP-адреса сервера (попробуйте добавить COOKIES_TEXT или выбрать другой язык)."
                )
            )

        safe_lang = re.sub(r"[^a-zA-Z0-9_-]", "", lang) or "sub"
        if format_type.lower() == "txt":
            clean_text = srt_to_clean_txt(content)
            txt_path = job_dir / f"{title}_{safe_lang}.txt"
            txt_path.write_text(clean_text, encoding="utf-8")
            return txt_path, f"{title}_{safe_lang}.txt", "text/plain; charset=utf-8"
        else:  # srt
            out_srt = job_dir / f"{title}_{safe_lang}.srt"
            srt_text = vtt_to_srt(content)
            out_srt.write_text(srt_text, encoding="utf-8")
            return out_srt, f"{title}_{safe_lang}.srt", "text/plain; charset=utf-8"
    finally:
        _subtitles_semaphore.release()
