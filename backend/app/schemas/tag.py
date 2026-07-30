"""标签 DTO。"""

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class NodeTagsUpdate(BaseModel):
    tag_ids: list[int]


class NodeTagsBatchAdd(BaseModel):
    node_ids: list[int] = Field(min_length=1)
    tag_ids: list[int] = Field(min_length=1)


class NodeTagsItem(BaseModel):
    node_id: int
    tags: list[TagResponse]
