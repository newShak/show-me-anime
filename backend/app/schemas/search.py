"""搜索 DTO。"""

from pydantic import BaseModel

from app.schemas.node import NodeResponse


class SearchResponse(BaseModel):
    q: str = ""
    tag_ids: list[int] = []
    tag_mode: str = "or"
    total: int
    items: list[NodeResponse]
