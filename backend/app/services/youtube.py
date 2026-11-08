"""YouTube extraction and media downloading service using yt-dlp and ffmpeg."""

import os
import re
import uuid
import shutil
import logging
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
    """Constructs base yt-dlp options including proxy, cookies, and timeouts."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "socket_timeout": settings.YTDLP_TIMEOUT_SECONDS,
        "extractor_args": {
            "youtube": {
                # Using mweb, web, and tv (avoiding ios which requires strict po_token)
                "player_client": ["mweb", "web", "tv"],
            }
        },
    }

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
    ydl_opts = get_ydl_base_opts({
        "skip_download": True,
        "ignore_no_formats_error": True,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
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
        logger.error(f"Unexpected extraction error for {url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка при извлечении метаданных: {str(e)}"
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
    unique_job_id = f"video_{uuid.uuid4().hex[:10]}"
    job_dir = settings.STORAGE_DIR / unique_job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Quality selector with flexible fallbacks (FFmpeg merges into MP4 via merge_output_format)
    if quality == "1080p":
        fmt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best"
    elif quality == "720p":
        fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best"
    elif quality == "480p":
        fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]/bestvideo+bestaudio/best"
    elif quality == "360p":
        fmt = "bestvideo[height<=360]+bestaudio/best[height<=360]/bestvideo+bestaudio/best"
    else:  # best
        fmt = "bestvideo+bestaudio/best"

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
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.error(f"Error downloading video {url} [{quality}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось скачать видео: {str(e)}"
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
        logger.error(f"Error downloading audio {url} [{audio_format}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось скачать аудио: {str(e)}"
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
    (Derived directly from analyze.py algorithm)
    """
    lines = []
    seen = set()
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
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)

    return "\n".join(lines)


def download_subtitles_file(url: str, lang: str = "ru", format_type: str = "txt") -> Tuple[Path, str, str]:
    """
    Extracts subtitles (manual first, then auto) using yt-dlp.
    Outputs clean .txt (without timestamps/duplicates) or standard .srt.
    Returns: (local_file_path, client_download_filename, mime_type)
    """
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
        logger.warning(f"Error checking manual subs: {e}")

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
            logger.warning(f"Error checking auto subs: {e}")

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка чтения субтитров: {e}"
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
