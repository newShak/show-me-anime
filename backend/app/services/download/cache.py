"""外站下载临时缓存目录。"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


@dataclass
class MoveResult:
    saved: int = 0
    skipped: int = 0


def job_cache_dir(settings: Settings, job_id: str) -> Path:
    root = settings.download_cache_dir.resolve()
    work = (root / job_id).resolve()
    if not str(work).startswith(str(root)):
        raise ValueError("cache path escapes download cache root")
    work.mkdir(parents=True, exist_ok=True)
    return work


def move_cache_files_to_dest(cache_dir: Path, dest_dir: Path, *, overwrite: bool = True) -> MoveResult:
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = MoveResult()
    for item in sorted(cache_dir.iterdir()):
        if not item.is_file():
            continue
        if item.name.startswith(".") or item.name == "_download.zip":
            continue
        if item.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        target = dest_dir / item.name
        if target.exists() and not overwrite:
            result.skipped += 1
            continue
        if target.exists():
            target.unlink()
        shutil.move(str(item), str(target))
        result.saved += 1
    return result


def cleanup_job_cache(cache_dir: Path) -> None:
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)


def clear_download_cache(settings: Settings) -> int:
    root = settings.download_cache_dir.resolve()
    if not root.exists():
        return 0
    deleted = 0
    for child in list(root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
            deleted += 1
        elif child.is_file():
            child.unlink(missing_ok=True)
            deleted += 1
    logger.info("download cache cleared root=%s deleted=%s", root, deleted)
    return deleted
