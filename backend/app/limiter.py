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
