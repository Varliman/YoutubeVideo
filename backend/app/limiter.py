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
