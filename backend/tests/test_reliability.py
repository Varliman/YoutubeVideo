"""
Automated reliability and regression test suite for youtube-analyzer-web.
"""

import os
import re
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import HTTPException
from starlette.testclient import TestClient

from backend.app.config import settings
from backend.app.limiter import validate_youtube_url
from backend.app.main import app, make_content_disposition
from backend.app.schemas import SubtitleOption
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
    _is_storyboard_or_non_media,
    get_ydl_base_opts,
    _CLIENT_PROFILES,
    _subtitle_sort_key,
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

    # 3. JS Runtime & Client Profile tests for yt-dlp 2026+
    def test_js_runtimes_node_explicitly_enabled(self):
        """Ensures get_ydl_base_opts explicitly sets js_runtimes['node'] so yt-dlp 2026+ uses Node.js."""
        opts = get_ydl_base_opts()
        self.assertIn("js_runtimes", opts)
        self.assertIn("node", opts["js_runtimes"])

    def test_client_profiles_cookie_free_first_and_no_tv(self):
        """Ensures first profile runs with use_cookies=False so android_vr/ios are not skipped by yt-dlp."""
        self.assertFalse(_CLIENT_PROFILES[0]["use_cookies"])
        has_missing_pot = False
        for prof in _CLIENT_PROFILES:
            y_args = prof.get("youtube_args", {})
            clients = y_args.get("player_client", [])
            self.assertNotIn("tv", clients)
            if "missing_pot" in y_args.get("formats", []):
                has_missing_pot = True
        self.assertTrue(has_missing_pot)

    def test_subtitle_sorting_ru_en_first(self):
        """Ensures Russian and English subtitles sort before other languages."""
        subs = [
            SubtitleOption(lang="qu", name="Quechua", is_auto=True, txt_url="", srt_url=""),
            SubtitleOption(lang="en", name="English", is_auto=True, txt_url="", srt_url=""),
            SubtitleOption(lang="ru", name="Russian", is_auto=True, txt_url="", srt_url=""),
        ]
        subs.sort(key=_subtitle_sort_key)
        self.assertEqual([s.lang for s in subs], ["ru", "en", "qu"])

    # 4. Concurrency serialization and 503 rejection
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

    # 5. URL Validation tests
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

    # 6. Pre-check feasibility with format verification & storyboard filtering
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
            "formats": [{"height": 2160}],
        }
        ok, msg, title = check_download_feasibility(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            kind="video",
            quality="720p"
        )
        self.assertFalse(ok)
        self.assertIn("Видео недоступно в качестве ≤720p", msg)

    def test_storyboard_filtering(self):
        """Ensures mhtml storyboards are detected as non-media."""
        sb_fmt = {"format_id": "sb0", "ext": "mhtml", "height": 180, "vcodec": "none", "acodec": "none"}
        real_fmt = {"format_id": "18", "ext": "mp4", "height": 360, "vcodec": "avc1.42001E", "acodec": "mp4a.40.2"}
        self.assertTrue(_is_storyboard_or_non_media(sb_fmt))
        self.assertFalse(_is_storyboard_or_non_media(real_fmt))

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

    # 7. Cleanup protected filenames
    def test_cleanup_protected_files(self):
        """Ensures cookies.txt, runtime_cookies.txt, .gitkeep, README.md are strictly protected."""
        self.assertIn("cookies.txt", PROTECTED_FILENAMES)
        self.assertIn("runtime_cookies.txt", PROTECTED_FILENAMES)
        self.assertIn(".gitkeep", PROTECTED_FILENAMES)
        self.assertIn("README.md", PROTECTED_FILENAMES)

    # 8. Health endpoint memory diagnostics
    def test_health_endpoint(self):
        """Tests /api/health reports RSS memory, nodejs_available, and concurrency constraints."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["concurrency_limit"], settings.MAX_CONCURRENT_DOWNLOADS)
        self.assertEqual(data["max_video_height"], settings.MAX_VIDEO_HEIGHT)
        self.assertIn("nodejs_available", data)
        self.assertIn("rss_mb", data)
        self.assertIn("oom_risk", data)
        self.assertIn(data["oom_risk"], ("low", "medium", "high"))

    # 9. Pre-check API endpoint integration
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

    # 10. Two-phase prepare & stream endpoint test
    @patch("backend.app.main.download_subtitles_file")
    def test_two_phase_prepare_and_stream(self, mock_dl_subs):
        """Tests /api/prepare-download followed by /api/stream/{token}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "subs_test"
            job_dir.mkdir(parents=True, exist_ok=True)
            sub_file = job_dir / "test_ru.txt"
            sub_file.write_text("Привет мир", encoding="utf-8")
            mock_dl_subs.return_value = (sub_file, "Видео_ru.txt", "text/plain; charset=utf-8")

            prep_res = self.client.get(
                "/api/prepare-download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&kind=transcript&lang=ru&format=txt"
            )
            self.assertEqual(prep_res.status_code, 200)
            prep_data = prep_res.json()
            self.assertTrue(prep_data["ok"])
            self.assertIn("token", prep_data)

            stream_res = self.client.get(prep_data["stream_url"])
            self.assertEqual(stream_res.status_code, 200)
            self.assertEqual(stream_res.text, "Привет мир")

    # 11. Cyrillic Content-Disposition Latin-1 encoding safety
    def test_content_disposition_cyrillic_latin1_safe(self):
        """Ensures Cyrillic filenames do not crash Starlette latin-1 header encoding."""
        header = make_content_disposition("Разбор_полетов_720p.mp4")
        encoded = header.encode("latin-1")
        self.assertIsInstance(encoded, bytes)
        self.assertIn("filename*=UTF-8''", header)

    # 12. WebVTT, JSON3, and XML cleaning and SRT conversion
    def test_vtt_json3_xml_cleaning(self):
        """Ensures WEBVTT, JSON3, and SRV3 XML subtitles convert cleanly to TXT and SRT."""
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
        self.assertEqual(srt_to_clean_txt(sample_vtt), "Привет & добро пожаловать!\nВторая строка текста'")
        converted_srt = vtt_to_srt(sample_vtt)
        self.assertIn("1\n00:00:01,000 --> 00:00:03,500\nПривет & добро пожаловать!", converted_srt)

        sample_json3 = json.dumps({
            "events": [
                {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Первая "}, {"utf8": "фраза"}]},
                {"tStartMs": 3000, "dDurationMs": 2000, "segs": [{"utf8": "Вторая фраза"}]},
            ]
        })
        self.assertEqual(srt_to_clean_txt(sample_json3), "Первая фраза\nВторая фраза")
        self.assertIn("00:00:01,000 --> 00:00:03,000", vtt_to_srt(sample_json3))

        sample_xml = '<transcript><text start="1.5" dur="2.0">Привет из XML</text></transcript>'
        self.assertEqual(srt_to_clean_txt(sample_xml), "Привет из XML")
        self.assertIn("00:00:01,500 --> 00:00:03,500", vtt_to_srt(sample_xml))

    # 13. Writable runtime cookies from COOKIES_TEXT
    def test_writable_cookies_from_text(self):
        """Ensures COOKIES_TEXT is normalized and written to a writable file in STORAGE_DIR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(settings, "STORAGE_DIR", tmpdir and tmp_path), \
                 patch.object(settings, "COOKIES_FILE", ""), \
                 patch.object(settings, "COOKIES_TEXT", ".youtube.com\\tTRUE\\t/\\tTRUE\\t0\\tSID\\t12345"):
                cookie_file = _prepare_writable_cookiefile()
                self.assertIsNotNone(cookie_file)
                content = Path(cookie_file).read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# Netscape HTTP Cookie File"))
                self.assertIn(".youtube.com", content)


if __name__ == "__main__":
    unittest.main()
