"""搜索 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.node import NodeResponse
from app.schemas.search import SearchResponse
from app.services.search import search_nodes_filtered

router = APIRouter(prefix="/search", tags=["search"])


def _parse_tag_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(part) for part in raw.split(",") if part.strip().isdigit()]


@router.get("", response_model=SearchResponse)
def search(
    q: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="逗号分隔的标签 id"),
    tag_mode: str = Query(default="or", pattern="^(or|and)$", description="多标签关系：or 任一，and 全部"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    text = (q or "").strip()
    tag_ids = _parse_tag_ids(tags)
    if not text and not tag_ids:
        raise HTTPException(status_code=400, detail="q or tags required")

    nodes, total = search_nodes_filtered(
        db, text or None, tag_ids or None, limit=limit, offset=offset, tag_mode=tag_mode
    )
    items = [NodeResponse.model_validate(node) for node in nodes]
    return SearchResponse(q=text, tag_ids=tag_ids, tag_mode=tag_mode, total=total, items=items)
