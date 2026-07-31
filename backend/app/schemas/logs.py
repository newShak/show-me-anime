"""日志查看 API DTO。"""

from pydantic import BaseModel, Field


class LogFileItem(BaseModel):
    name: str
    size: int
    modified_at: float


class LogFileListResponse(BaseModel):
    dir: str
    enabled: bool
    items: list[LogFileItem]


class LogContentResponse(BaseModel):
    file: str
    content: str
    offset: int
    reset: bool = False
    append: bool = False


class LogTailQuery(BaseModel):
    file: str = "app.log"
    tail_lines: int = Field(default=500, ge=1, le=5000, alias="tailLines")
    offset: int = Field(default=0, ge=0)
