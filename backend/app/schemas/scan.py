"""扫描任务 DTO。"""

from typing import Literal

from pydantic import BaseModel

ScanMode = Literal["incremental", "full"]


class ScanTriggerRequest(BaseModel):
    mode: ScanMode = "incremental"


class ScanJobResponse(BaseModel):
    id: int
    status: str
    source: str = "manual"
    mode: str = "incremental"
    started_at: float | None
    finished_at: float | None
    added: int
    updated: int
    removed: int
    message: str | None

    model_config = {"from_attributes": True}
