"""标签 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Node, NodeTag, Tag
from app.db.session import get_db
from app.schemas.tag import NodeTagsUpdate, TagCreate, TagResponse
from app.services.node_admin import sync_node_search_index

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name).all()


@router.post("", response_model=TagResponse)
def create_tag(body: TagCreate, db: Session = Depends(get_db)) -> Tag:
    exists = db.query(Tag).filter(Tag.name == body.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="tag already exists")
    tag = Tag(name=body.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="tag not found")
    nodes = db.query(Node).join(NodeTag, NodeTag.node_id == Node.id).filter(NodeTag.tag_id == tag_id).all()
    db.query(NodeTag).filter(NodeTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.commit()
    for node in nodes:
        sync_node_search_index(db, node)
    db.commit()
    return {"status": "ok"}


@router.get("/nodes/{node_id}", response_model=list[TagResponse])
def list_node_tags(node_id: int, db: Session = Depends(get_db)) -> list[Tag]:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return (
        db.query(Tag)
        .join(NodeTag, NodeTag.tag_id == Tag.id)
        .filter(NodeTag.node_id == node_id)
        .order_by(Tag.name)
        .all()
    )


@router.put("/nodes/{node_id}", response_model=list[TagResponse])
def set_node_tags(node_id: int, body: NodeTagsUpdate, db: Session = Depends(get_db)) -> list[Tag]:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")

    db.query(NodeTag).filter(NodeTag.node_id == node_id).delete()
    tags: list[Tag] = []
    for tag_id in body.tag_ids:
        tag = db.get(Tag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail=f"tag {tag_id} not found")
        db.add(NodeTag(node_id=node_id, tag_id=tag_id))
        tags.append(tag)
    db.commit()
    sync_node_search_index(db, node)
    db.commit()
    return tags
