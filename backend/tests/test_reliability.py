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
