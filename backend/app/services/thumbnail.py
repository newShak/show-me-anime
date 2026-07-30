"""缩略图按需生成与缓存。"""

import hashlib
import logging
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def thumb_cache_path(thumb_dir: Path, node_path: str, filename: str) -> Path:
    key = hashlib.sha256(f"{node_path}/{filename}".encode()).hexdigest()
    return thumb_dir / f"{key}.webp"


def ensure_thumbnail(source: Path, dest: Path, max_size: int) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_mtime >= source.stat().st_mtime:
        logger.debug("thumb cache hit dest=%s", dest.name)
        return dest

    try:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((max_size, max_size))
            img.save(dest, format="WEBP", quality=85)
        logger.info("thumb generated source=%s dest=%s", source.name, dest.name)
    except OSError as exc:
        logger.warning("thumb failed source=%s error=%s", source, exc)
        raise
    return dest


def get_or_create_thumbnail(
    source: Path,
    node_path: str,
    filename: str,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    dest = thumb_cache_path(settings.thumb_dir, node_path, filename)
    return ensure_thumbnail(source, dest, settings.thumb_max_size)


def ensure_thumbnail_bytes(data: bytes, dest: Path, max_size: int, source_mtime: float) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_mtime >= source_mtime:
        logger.debug("thumb cache hit dest=%s", dest.name)
        return dest

    try:
        with Image.open(BytesIO(data)) as img:
            img = img.convert("RGB")
            img.thumbnail((max_size, max_size))
            img.save(dest, format="WEBP", quality=85)
        logger.info("thumb generated from archive dest=%s", dest.name)
    except OSError as exc:
        logger.warning("thumb failed dest=%s error=%s", dest, exc)
        raise
    return dest


def get_or_create_thumbnail_bytes(
    data: bytes,
    node_path: str,
    filename: str,
    source_mtime: float,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    dest = thumb_cache_path(settings.thumb_dir, node_path, filename)
    return ensure_thumbnail_bytes(data, dest, settings.thumb_max_size, source_mtime)


def clear_thumbnail_cache(settings: Settings | None = None) -> int:
    """删除缩略图缓存目录内全部 .webp，返回清除数量。"""
    settings = settings or get_settings()
    thumb_dir = settings.thumb_dir
    if not thumb_dir.is_dir():
        logger.info("thumb cache clear skipped dir missing=%s", thumb_dir)
        return 0
    deleted = 0
    for path in thumb_dir.glob("*.webp"):
        path.unlink(missing_ok=True)
        deleted += 1
    logger.info("thumb cache cleared count=%s dir=%s", deleted, thumb_dir)
    return deleted
