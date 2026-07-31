"""节点与相册相关 DTO。"""

from pydantic import BaseModel, Field


class NodeResponse(BaseModel):
    id: int
    parent_id: int | None
    name: str
    path: str
    node_type: str
    source_type: str
    image_count: int
    subdir_count: int
    archive_count: int = 0
    cover_rel_path: str | None = None
    cover_manual: bool = False
    dir_mtime: float | None = None
    created_at: float | None = None

    model_config = {"from_attributes": True}


class RecentNodesResponse(BaseModel):
    total: int
    items: list[NodeResponse]


class ImageItem(BaseModel):
    index: int
    filename: str


class ImageListResponse(BaseModel):
    node_id: int
    total: int
    items: list[ImageItem]


class CoverCandidate(BaseModel):
    value: str
    label: str
    source_node_id: int


class CoverCandidateListResponse(BaseModel):
    node_id: int
    items: list[CoverCandidate]


class NodeUpdate(BaseModel):
    node_type: str | None = None
    cover_rel_path: str | None = None
    cover_index: int | None = Field(default=None, ge=0)
    cover_manual: bool | None = None


class NodeBatchDelete(BaseModel):
    ids: list[int] = Field(min_length=1)


class NodeBatchDeleteResponse(BaseModel):
    deleted: int
    errors: list[str] = []


class NodeMove(BaseModel):
    ids: list[int] = Field(min_length=1)
    target_parent_id: int | None = None


class NodeMoveResponse(BaseModel):
    moved: int
    errors: list[str] = []
