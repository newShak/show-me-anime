"""缩略图按需生成与缓存。"""

import hashlib
from pathlib import Path

from PIL import Image

from app.config import Settings, get_settings


def thumb_cache_path(thumb_dir: Path, node_path: str, filename: str) -> Path:
    key = hashlib.sha256(f"{node_path}/{filename}".encode()).hexdigest()
    return thumb_dir / f"{key}.webp"


def ensure_thumbnail(source: Path, dest: Path, max_size: int) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_mtime >= source.stat().st_mtime:
        return dest

    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        img.save(dest, format="WEBP", quality=85)
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
