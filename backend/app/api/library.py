"""最近浏览与收藏 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Node
from app.db.session import get_db
from app.schemas.library import FavoriteToggleResponse, FavoritesResponse
from app.schemas.node import NodeResponse
from app.services.library import (
    clear_favorites,
    clear_recent_views,
    list_favorite_ids,
    list_favorite_nodes,
    list_recent_nodes,
    toggle_favorite,
    touch_recent_view,
    trim_recent_views,
)

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/recent", response_model=list[NodeResponse])
def get_recent_views(
    limit: int | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[Node]:
    cap = limit if limit is not None else settings.recent_view_limit
    return list_recent_nodes(db, min(max(cap, 1), 100))


@router.post("/recent/{node_id}", status_code=204)
def post_recent_view(
    node_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    if db.get(Node, node_id) is None:
        raise HTTPException(status_code=404, detail="node not found")
    touch_recent_view(db, node_id)
    trim_recent_views(db, settings.recent_view_limit)
    db.commit()


@router.delete("/recent", status_code=204)
def delete_recent_views(db: Session = Depends(get_db)) -> None:
    clear_recent_views(db)
    db.commit()


@router.get("/favorites/ids", response_model=list[int])
def get_favorite_ids(db: Session = Depends(get_db)) -> list[int]:
    return list_favorite_ids(db)


@router.get("/favorites", response_model=FavoritesResponse)
def get_favorites(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> FavoritesResponse:
    items, total = list_favorite_nodes(db, offset, limit)
    return FavoritesResponse(total=total, items=items)


@router.post("/favorites/{node_id}", response_model=FavoriteToggleResponse)
def post_toggle_favorite(node_id: int, db: Session = Depends(get_db)) -> FavoriteToggleResponse:
    if db.get(Node, node_id) is None:
        raise HTTPException(status_code=404, detail="node not found")
    favorited = toggle_favorite(db, node_id)
    db.commit()
    return FavoriteToggleResponse(node_id=node_id, favorited=favorited)


@router.delete("/favorites", status_code=204)
def delete_favorites(db: Session = Depends(get_db)) -> None:
    clear_favorites(db)
    db.commit()
