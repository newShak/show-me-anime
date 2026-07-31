"""下载记录关联路径的字节统计。"""

from pathlib import Path

from app.config import Settings
from app.db.models import DownloadRecord


def cache_dir_size(cache_dir: Path) -> int:
    if not cache_dir.is_dir():
        return 0
    total = 0
    for item in cache_dir.iterdir():
        if item.name.startswith(".") and item.name != "_download.zip":
            continue
        if not item.is_file():
            continue
        try:
            total += item.stat().st_size
        except OSError:
            pass
    return total


def dest_dir_size(dest_dir: Path) -> int:
    if not dest_dir.is_dir():
        return 0
    total = 0
    for item in dest_dir.iterdir():
        if not item.is_file() or item.name.startswith("."):
            continue
        try:
            total += item.stat().st_size
        except OSError:
            pass
    return total


def record_size_bytes(settings: Settings, record: DownloadRecord) -> int:
    dest = (settings.gallery_root / record.target_rel_path).resolve()
    cache = settings.download_cache_dir / record.id

    if record.status in {"running", "pending"}:
        cache_size = cache_dir_size(cache)
        if cache_size > 0:
            return cache_size

    dest_size = dest_dir_size(dest)
    if dest_size > 0:
        return dest_size

    return cache_dir_size(cache)
