"""相册图片列表：按需读盘 + 自然排序 + 内存缓存。"""

import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Node
from app.utils.natural_sort import sorted_image_names
from app.utils.paths import is_image_file


@dataclass
class CacheEntry:
    dir_mtime: float
    filenames: list[str]
    cached_at: float


class AlbumReader:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._cache: dict[int, CacheEntry] = {}

    def invalidate(self, node_id: int | None = None) -> None:
        if node_id is None:
            self._cache.clear()
            return
        self._cache.pop(node_id, None)

    def list_images(self, db: Session, node: Node) -> list[str]:
        dir_path = self.settings.gallery_root / node.path
        if not dir_path.is_dir():
            return []

        dir_mtime = dir_path.stat().st_mtime
        cached = self._cache.get(node.id)
        ttl = self.settings.album_list_cache_ttl
        if cached and cached.dir_mtime == dir_mtime and time.time() - cached.cached_at < ttl:
            return cached.filenames

        filenames = sorted_image_names(
            [entry.name for entry in dir_path.iterdir() if entry.is_file() and is_image_file(entry.name)]
        )
        names = filenames
        self._cache[node.id] = CacheEntry(dir_mtime=dir_mtime, filenames=names, cached_at=time.time())

        if node.image_count != len(names) or node.dir_mtime != dir_mtime:
            node.image_count = len(names)
            node.dir_mtime = dir_mtime
            if names and not node.cover_rel_path:
                node.cover_rel_path = names[0]
            db.commit()

        return names


_album_reader: AlbumReader | None = None


def get_album_reader() -> AlbumReader:
    global _album_reader
    if _album_reader is None:
        _album_reader = AlbumReader()
    return _album_reader


def reset_album_reader() -> None:
    global _album_reader
    _album_reader = None
