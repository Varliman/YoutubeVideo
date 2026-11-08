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
