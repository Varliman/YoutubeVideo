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


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    ffmpeg_available: bool
    proxy_configured: bool
    cookies_configured: bool
    storage_dir: str
