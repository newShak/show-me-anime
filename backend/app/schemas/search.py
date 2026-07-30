"""搜索 DTO。"""

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: int
    name: str
    path: str
    node_type: str
    image_count: int


class SearchResponse(BaseModel):
    q: str = ""
    tag_ids: list[int] = []
    total: int
    items: list[SearchResultItem]
