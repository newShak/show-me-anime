"""配置相关 DTO。"""

from typing import Literal

from pydantic import BaseModel, Field

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class SettingsResponse(BaseModel):
    gallery_root: str
    thumb_dir: str
    database_url: str
    thumb_max_size: int
    watch_enabled: bool
    watch_debounce_seconds: int
    album_list_cache_ttl: int
    log_level: LogLevel = "INFO"
    host: str
    port: int


class SettingsUpdate(BaseModel):
    gallery_root: str | None = None
    thumb_dir: str | None = None
    thumb_max_size: int | None = Field(default=None, ge=64, le=2000)
    watch_enabled: bool | None = None
    watch_debounce_seconds: int | None = Field(default=None, ge=1, le=60)
    log_level: LogLevel | None = None


class SettingsSaveResponse(SettingsResponse):
    message: str | None = None
    needs_rescan: bool = False


class ThumbRebuildResponse(BaseModel):
    deleted: int
    message: str
