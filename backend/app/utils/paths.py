"""路径与图片文件工具。"""

from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
ARCHIVE_EXTENSIONS = {".zip", ".cbz"}


def is_image_file(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTENSIONS


def is_archive_file(name: str) -> bool:
    return Path(name).suffix.lower() in ARCHIVE_EXTENSIONS


def archive_display_name(filename: str) -> str:
    """压缩包节点展示名（去掉扩展名）。"""
    return Path(filename).stem


def safe_resolve(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError("path traversal")
    return target


def rel_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
