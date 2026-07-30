"""节点与相册 API。"""

import mimetypes
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app import constants
from app.constants import ORDER_ASC, SORT_NAME
from app.config import get_settings
from app.db.models import Node, ReadProgress
from app.db.session import get_db
from app.schemas.node import (
    ImageItem,
    ImageListResponse,
    NodeBatchDelete,
    NodeBatchDeleteResponse,
    NodeResponse,
    NodeUpdate,
)
from app.schemas.progress import ProgressResponse, ProgressUpdate
from app.services.album_reader import AlbumReader, get_album_reader
from app.services.media import ImageSource, resolve_cover_source, resolve_image_source
from app.services.node_admin import sync_node_search_index
from app.services.node_delete import delete_nodes
from app.services.node_sort import SORT_FIELDS, SORT_ORDERS, sort_nodes
from app.services.thumbnail import get_or_create_thumbnail, get_or_create_thumbnail_bytes

router = APIRouter(tags=["nodes"])


def _image_response(source: ImageSource) -> FileResponse | Response:
    media_type = mimetypes.guess_type(source.filename)[0] or "application/octet-stream"
    cache = {"Cache-Control": "private, max-age=3600, must-revalidate"}
    if source.data is not None:
        headers = {**cache, "ETag": f'W/"{source.mtime}-{len(source.data)}"'}
        return Response(content=source.data, media_type=media_type, headers=headers)
    stat = source.path.stat()
    return FileResponse(
        source.path,
        media_type=media_type,
        filename=source.filename,
        stat_result=stat,
        headers=cache,
    )


def _thumb_path(node: Node, source: ImageSource, settings) -> Path:
    if source.path is not None:
        return get_or_create_thumbnail(source.path, node.path, source.filename, settings)
    return get_or_create_thumbnail_bytes(
        source.data or b"",
        node.path,
        source.filename,
        source.mtime,
        settings,
    )


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(
    parent_id: int | None = Query(default=None),
    sort_by: str = Query(default=SORT_NAME),
    sort_order: str = Query(default=ORDER_ASC),
    db: Session = Depends(get_db),
) -> list[Node]:
    if sort_by not in SORT_FIELDS:
        raise HTTPException(status_code=400, detail="invalid sort_by")
    if sort_order not in SORT_ORDERS:
        raise HTTPException(status_code=400, detail="invalid sort_order")

    query = db.query(Node)
    if parent_id is None:
        query = query.filter(Node.parent_id.is_(None))
    else:
        query = query.filter(Node.parent_id == parent_id)
    return sort_nodes(query.all(), sort_by, sort_order)


@router.get("/nodes/progress", response_model=list[ProgressResponse])
def list_nodes_progress(
    ids: str = Query(..., description="逗号分隔的 node id"),
    db: Session = Depends(get_db),
) -> list[ProgressResponse]:
    """批量读取相册阅读进度。"""
    node_ids = [int(part) for part in ids.split(",") if part.strip().isdigit()]
    if not node_ids:
        return []

    rows = db.query(ReadProgress).filter(ReadProgress.node_id.in_(node_ids)).all()
    row_map = {row.node_id: row for row in rows}
    return [
        ProgressResponse(
            node_id=nid,
            page_index=row_map[nid].page_index if nid in row_map else 0,
            updated_at=row_map[nid].updated_at if nid in row_map else None,
        )
        for nid in node_ids
    ]


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


@router.post("/nodes/batch-delete", response_model=NodeBatchDeleteResponse)
def batch_delete_nodes(
    body: NodeBatchDelete,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
) -> NodeBatchDeleteResponse:
    deleted, errors = delete_nodes(db, body.ids)
    reader.invalidate()
    return NodeBatchDeleteResponse(deleted=deleted, errors=errors)


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


@router.get("/nodes/{node_id}/images/{index}/file", response_model=None)
def get_image_file(
    node_id: int,
    index: int,
    db: Session = Depends(get_db),
    reader: AlbumReader = Depends(get_album_reader),
):
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    source = resolve_image_source(node, index, db, reader)
    return _image_response(source)


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
    source = resolve_image_source(node, index, db, reader, settings)
    thumb_path = _thumb_path(node, source, settings)
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
    source = resolve_cover_source(node, db, reader, settings)
    thumb_path = _thumb_path(node, source, settings)
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
