"""标签 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Node, NodeTag, Tag
from app.db.session import get_db
from app.schemas.tag import NodeTagsBatchAdd, NodeTagsItem, NodeTagsUpdate, TagCreate, TagEnsureRequest, TagEnsureResponse, TagPageResponse, TagResponse
from app.services.node_admin import sync_node_search_index
from app.services.tag_admin import ensure_tags_by_names

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name).all()


@router.get("/paged", response_model=TagPageResponse)
def list_tags_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
) -> TagPageResponse:
    query = db.query(Tag).order_by(Tag.name)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return TagPageResponse(items=items, total=total, page=page, page_size=page_size)


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


@router.post("/ensure", response_model=TagEnsureResponse)
def ensure_tags(body: TagEnsureRequest, db: Session = Depends(get_db)) -> TagEnsureResponse:
    tags = ensure_tags_by_names(db, body.names)
    db.commit()
    for tag in tags:
        db.refresh(tag)
    return TagEnsureResponse(tags=tags)


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


@router.get("/nodes/tags", response_model=list[NodeTagsItem])
def list_nodes_tags(
    ids: str = Query(..., description="逗号分隔的 node id"),
    db: Session = Depends(get_db),
) -> list[NodeTagsItem]:
    node_ids = [int(part) for part in ids.split(",") if part.strip().isdigit()]
    if not node_ids:
        return []

    rows = (
        db.query(NodeTag.node_id, Tag)
        .join(Tag, Tag.id == NodeTag.tag_id)
        .filter(NodeTag.node_id.in_(node_ids))
        .order_by(Tag.name)
        .all()
    )
    grouped: dict[int, list[Tag]] = {nid: [] for nid in node_ids}
    for node_id, tag in rows:
        grouped[node_id].append(tag)
    return [NodeTagsItem(node_id=nid, tags=grouped[nid]) for nid in node_ids]


@router.post("/nodes/batch-add")
def batch_add_node_tags(body: NodeTagsBatchAdd, db: Session = Depends(get_db)) -> dict[str, int]:
    tags = [db.get(Tag, tag_id) for tag_id in body.tag_ids]
    if any(t is None for t in tags):
        raise HTTPException(status_code=404, detail="tag not found")

    updated = 0
    for node_id in body.node_ids:
        node = db.get(Node, node_id)
        if node is None:
            continue
        existing = {nt.tag_id for nt in db.query(NodeTag).filter(NodeTag.node_id == node_id).all()}
        added = False
        for tag_id in body.tag_ids:
            if tag_id not in existing:
                db.add(NodeTag(node_id=node_id, tag_id=tag_id))
                added = True
        if added:
            sync_node_search_index(db, node)
            updated += 1
    db.commit()
    return {"updated": updated}


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


@router.delete("/nodes/{node_id}/tags/{tag_id}")
def remove_node_tag(node_id: int, tag_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    deleted = (
        db.query(NodeTag)
        .filter(NodeTag.node_id == node_id, NodeTag.tag_id == tag_id)
        .delete(synchronize_session=False)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="tag not on node")
    db.commit()
    sync_node_search_index(db, node)
    db.commit()
    return {"status": "ok"}
