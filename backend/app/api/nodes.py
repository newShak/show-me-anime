"""节点与相册 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Node
from app.db.session import get_db
from app.schemas.node import ImageItem, ImageListResponse, NodeResponse
from app.services.album_reader import AlbumReader, get_album_reader

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
