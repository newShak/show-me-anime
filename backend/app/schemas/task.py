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


class TaskPurgeRequest(BaseModel):
    """按时间范围清理任务记录。"""

    model_config = ConfigDict(populate_by_name=True)

    start_time: float = Field(alias="startTime")
    end_time: float = Field(alias="endTime")


class TaskPurgeResponse(BaseModel):
    """清理任务记录结果。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    deleted_scans: int = Field(alias="deletedScans")
    deleted_logs: int = Field(alias="deletedLogs")
    deleted: int
