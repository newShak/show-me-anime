"""图片路径解析。"""

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Node
from app.services.album_reader import AlbumReader


def resolve_image_file(
    node: Node,
    index: int,
    db: Session,
    reader: AlbumReader,
    settings: Settings | None = None,
) -> tuple[Path, str]:
    if node.node_type == "container":
        raise HTTPException(status_code=400, detail="container node has no images")

    settings = settings or get_settings()
    names = reader.list_images(db, node)
    if index < 0 or index >= len(names):
        raise HTTPException(status_code=404, detail="image not found")

    filename = names[index]
    dir_path = (settings.gallery_root / node.path).resolve()
    file_path = (dir_path / filename).resolve()
    if not str(file_path).startswith(str(dir_path)):
        raise HTTPException(status_code=400, detail="invalid path")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return file_path, filename


def resolve_cover_file(
    node: Node,
    db: Session,
    reader: AlbumReader,
    settings: Settings | None = None,
) -> tuple[Path, str]:
    settings = settings or get_settings()
    names = reader.list_images(db, node)
    if not names:
        raise HTTPException(status_code=404, detail="no cover image")

    filename = node.cover_rel_path if node.cover_rel_path in names else names[0]
    dir_path = (settings.gallery_root / node.path).resolve()
    file_path = (dir_path / filename).resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="cover not found")
    return file_path, filename
