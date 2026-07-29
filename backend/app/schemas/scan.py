"""扫描任务 DTO。"""

from pydantic import BaseModel


class ScanJobResponse(BaseModel):
    id: int
    status: str
    started_at: float | None
    finished_at: float | None
    added: int
    updated: int
    removed: int
    message: str | None

    model_config = {"from_attributes": True}
