"""标签 DTO。"""

from pydantic import BaseModel, ConfigDict, Field


class TagResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TagPageResponse(BaseModel):
    """标签分页结果。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[TagResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TagEnsureRequest(BaseModel):
    names: list[str] = Field(default_factory=list)


class TagEnsureResponse(BaseModel):
    tags: list[TagResponse]


class NodeTagsUpdate(BaseModel):
    tag_ids: list[int]


class NodeTagsBatchAdd(BaseModel):
    node_ids: list[int] = Field(min_length=1)
    tag_ids: list[int] = Field(min_length=1)


class NodeTagsItem(BaseModel):
    node_id: int
    tags: list[TagResponse]
