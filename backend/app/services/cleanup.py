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
