"""节点与相册相关 DTO。"""

from pydantic import BaseModel


class NodeResponse(BaseModel):
    id: int
    parent_id: int | None
    name: str
    path: str
    node_type: str
    source_type: str
    image_count: int
    cover_rel_path: str | None

    model_config = {"from_attributes": True}


class ImageItem(BaseModel):
    index: int
    filename: str


class ImageListResponse(BaseModel):
    node_id: int
    total: int
    items: list[ImageItem]
