"""图片路径解析。"""

import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node
from app.services.album_reader import AlbumReader
from app.services.archive_reader import read_archive_entry


@dataclass
class ImageSource:
    """图片数据来源：文件夹路径或压缩包内存字节。"""

    filename: str
    path: Path | None = None
    data: bytes | None = None
    mtime: float = 0.0


def resolve_image_source(
    node: Node,
    index: int,
    db: Session,
    reader: AlbumReader,
    settings: Settings | None = None,
) -> ImageSource:
    if node.node_type == "container":
        raise HTTPException(status_code=400, detail="container node has no images")

    settings = settings or get_settings()
    names = reader.list_images(db, node)
    if index < 0 or index >= len(names):
        raise HTTPException(status_code=404, detail="image not found")

    filename = names[index]
    if node.source_type == constants.SOURCE_ZIP:
        return _resolve_archive_source(settings, node.path, filename)

    dir_path = (settings.gallery_root / node.path).resolve()
    file_path = (dir_path / filename).resolve()
    if not str(file_path).startswith(str(dir_path)):
        raise HTTPException(status_code=400, detail="invalid path")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return ImageSource(
        filename=Path(filename).name,
        path=file_path,
        mtime=file_path.stat().st_mtime,
    )


def resolve_cover_source(
    node: Node,
    db: Session,
    reader: AlbumReader,
    settings: Settings | None = None,
) -> ImageSource:
    settings = settings or get_settings()
    cover = node.cover_rel_path
    if not cover:
        raise HTTPException(status_code=404, detail="no cover image")

    if node.source_type == constants.SOURCE_FOLDER:
        if "::" in cover:
            archive_name, entry = cover.split("::", 1)
            archive_path = f"{node.path}/{archive_name}".strip("/") if node.path else archive_name
            return _resolve_archive_source(settings, archive_path, entry)

        dir_path = (settings.gallery_root / node.path).resolve()
        inherited = (dir_path / cover).resolve()
        if str(inherited).startswith(str(dir_path)) and inherited.is_file():
            return ImageSource(
                filename=Path(cover).name,
                path=inherited,
                mtime=inherited.stat().st_mtime,
            )

    names = reader.list_images(db, node)
    if not names:
        raise HTTPException(status_code=404, detail="no cover image")

    filename = cover if cover in names else names[0]
    if node.source_type == constants.SOURCE_ZIP:
        return _resolve_archive_source(settings, node.path, filename)

    dir_path = (settings.gallery_root / node.path).resolve()
    file_path = (dir_path / filename).resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="cover not found")
    return ImageSource(
        filename=Path(filename).name,
        path=file_path,
        mtime=file_path.stat().st_mtime,
    )


def _resolve_archive_source(settings: Settings, node_path: str, entry_name: str) -> ImageSource:
    archive_path = (settings.gallery_root / node_path).resolve()
    root = settings.gallery_root.resolve()
    if not str(archive_path).startswith(str(root)) or not archive_path.is_file():
        raise HTTPException(status_code=404, detail="archive not found")
    try:
        data = read_archive_entry(archive_path, entry_name)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=404, detail="image not found") from exc
    return ImageSource(
        filename=Path(entry_name).name,
        data=data,
        mtime=archive_path.stat().st_mtime,
    )
