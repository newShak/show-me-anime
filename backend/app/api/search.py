"""集合搜索 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.search import search_nodes

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    nodes, total = search_nodes(db, q, limit=limit, offset=offset)
    items = [
        SearchResultItem(
            id=node.id,
            name=node.name,
            path=node.path,
            node_type=node.node_type,
            image_count=node.image_count,
        )
        for node in nodes
    ]
    return SearchResponse(q=q, total=total, items=items)
