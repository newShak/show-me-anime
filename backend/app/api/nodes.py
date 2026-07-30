"""节点与相册 API。"""

import mimetypes
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import constants
from app.config import get_settings
from app.db.models import Node, ReadProgress
from app.db.session import get_db
from app.schemas.node import ImageItem, ImageListResponse, NodeResponse, NodeUpdate
from app.schemas.progress import ProgressResponse, ProgressUpdate
from app.services.album_reader import AlbumReader, get_album_reader
from app.services.media import resolve_cover_file, resolve_image_file
from app.services.node_admin import sync_node_search_index
from app.services.thumbnail import get_or_create_thumbnail

router = APIRouter(tags=["nodes"])


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(
    parent_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Node]:
    query = db.query(Node)
    if parent_id is None:
        query = query.filter(Node.parent_id.is_(None))
    else:
        query = query.filter(Node.parent_id == parent_id)
    return query.order_by(Node.name).all()


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(node_id: int, db: Session = Depends(get_db)) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
def update_node(
    node_id: int,
    body: NodeUpdate,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")

    data = body.model_dump(exclude_none=True)
    if not data:
        return node

    if "node_type" in data:
        allowed = {constants.CONTAINER, constants.ALBUM, constants.BOTH}
        if data["node_type"] not in allowed:
            raise HTTPException(status_code=400, detail="invalid node_type")
        node.node_type = data["node_type"]

    if "cover_index" in data:
        names = reader.list_images(db, node)
        idx = data["cover_index"]
        if idx >= len(names):
            raise HTTPException(status_code=400, detail="cover_index out of range")
        node.cover_rel_path = names[idx]
    elif "cover_rel_path" in data:
        node.cover_rel_path = data["cover_rel_path"]

    node.updated_at = time.time()
    db.commit()
    db.refresh(node)
    sync_node_search_index(db, node)
    db.commit()
    return node


@router.get("/nodes/{node_id}/images", response_model=ImageListResponse)
def list_node_images(
    node_id: int,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> ImageListResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    if node.node_type == "container":
        raise HTTPException(status_code=400, detail="container node has no images")

    names = reader.list_images(db, node)
    return ImageListResponse(
        node_id=node.id,
        total=len(names),
        items=[ImageItem(index=i, filename=name) for i, name in enumerate(names)],
    )


@router.get("/nodes/{node_id}/images/{index}/file")
def get_image_file(
    node_id: int,
    index: int,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> FileResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    file_path, filename = resolve_image_file(node, index, db, reader)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=filename)


@router.get("/nodes/{node_id}/images/{index}/thumb")
def get_image_thumb(
    node_id: int,
    index: int,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> FileResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    settings = get_settings()
    file_path, filename = resolve_image_file(node, index, db, reader, settings)
    thumb_path = get_or_create_thumbnail(file_path, node.path, filename, settings)
    return FileResponse(thumb_path, media_type="image/webp")


@router.get("/nodes/{node_id}/cover/thumb")
def get_cover_thumb(
    node_id: int,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> FileResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    settings = get_settings()
    file_path, filename = resolve_cover_file(node, db, reader, settings)
    thumb_path = get_or_create_thumbnail(file_path, node.path, filename, settings)
    return FileResponse(thumb_path, media_type="image/webp")


@router.get("/nodes/{node_id}/progress", response_model=ProgressResponse)
def get_progress(node_id: int, db: Session = Depends(get_db)) -> ProgressResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    row = db.get(ReadProgress, node_id)
    if row is None:
        return ProgressResponse(node_id=node_id, page_index=0, updated_at=None)
    return ProgressResponse(node_id=node_id, page_index=row.page_index, updated_at=row.updated_at)


@router.put("/nodes/{node_id}/progress", response_model=ProgressResponse)
def save_progress(
    node_id: int,
    body: ProgressUpdate,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> ProgressResponse:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    if node.node_type == "container":
        raise HTTPException(status_code=400, detail="container node has no images")

    total = len(reader.list_images(db, node))
    if body.page_index >= total:
        raise HTTPException(status_code=400, detail="page_index out of range")

    row = db.get(ReadProgress, node_id)
    now = time.time()
    if row is None:
        row = ReadProgress(node_id=node_id, page_index=body.page_index, updated_at=now)
        db.add(row)
    else:
        row.page_index = body.page_index
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return ProgressResponse(node_id=node_id, page_index=row.page_index, updated_at=row.updated_at)
