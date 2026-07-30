"""阅读进度 DTO。"""

from pydantic import BaseModel, Field


class ProgressResponse(BaseModel):
    node_id: int
    page_index: int
    updated_at: float | None = None


class ProgressUpdate(BaseModel):
    page_index: int = Field(ge=0)
