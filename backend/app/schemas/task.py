"""任务记录 DTO。"""

from pydantic import BaseModel, ConfigDict, Field


class TaskRecordResponse(BaseModel):
    """管理页任务执行记录。"""

    id: int
    task_type: str
    status: str
    source: str | None = None
    mode: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    added: int | None = None
    updated: int | None = None
    removed: int | None = None
    message: str | None = None


class TaskRecordPageResponse(BaseModel):
    """任务记录分页结果。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[TaskRecordResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
