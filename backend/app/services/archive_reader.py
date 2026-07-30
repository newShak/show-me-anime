"""ZIP/CBZ 压缩包读取（内存，不写磁盘缓存）。"""

import logging
import zipfile
from pathlib import Path

from app.utils.natural_sort import sorted_image_names
from app.utils.paths import is_image_file

logger = logging.getLogger(__name__)


def _skip_entry(name: str) -> bool:
    parts = Path(name.replace("\\", "/")).parts
    return any(part.startswith(".") or part == "__MACOSX" for part in parts)


def list_archive_images(archive_path: Path) -> list[str]:
    """列出压缩包内图片（自然排序，路径相对包根）。"""
    try:
        with zipfile.ZipFile(archive_path) as zf:
            names = [
                name.replace("\\", "/")
                for name in zf.namelist()
                if not name.endswith("/") and is_image_file(name) and not _skip_entry(name)
            ]
    except (OSError, zipfile.BadZipFile) as exc:
        logger.warning("archive list failed path=%s error=%s", archive_path, exc)
        raise
    return sorted_image_names(names)


def read_archive_entry(archive_path: Path, entry_name: str) -> bytes:
    """从压缩包读取单张图片到内存。"""
    try:
        with zipfile.ZipFile(archive_path) as zf:
            return zf.read(entry_name)
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        logger.warning("archive read failed path=%s entry=%s error=%s", archive_path, entry_name, exc)
        raise
