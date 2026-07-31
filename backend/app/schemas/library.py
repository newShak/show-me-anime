"""最近浏览与收藏 DTO。"""

from pydantic import BaseModel

from app.schemas.node import NodeResponse


class FavoriteToggleResponse(BaseModel):
    node_id: int
    favorited: bool


class FavoritesResponse(BaseModel):
    total: int
    items: list[NodeResponse]
