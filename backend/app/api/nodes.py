"""节点与相册 API。"""

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Node
from app.db.session import get_db
from app.schemas.node import ImageItem, ImageListResponse, NodeResponse
from app.services.album_reader import AlbumReader, get_album_reader
from app.services.media import resolve_cover_file, resolve_image_file
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
