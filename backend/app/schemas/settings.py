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
    log_dir: str = "/data/logs"
    log_file_enabled: bool = True
    log_file_max_bytes: int = 10 * 1024 * 1024
    log_file_retention_days: int = 30
    recent_view_limit: int = 20
    recent_added_limit: int = 20
    host: str
    port: int
    download_proxy_enabled: bool = False
    download_proxy: str = ""
    download_default_subdir: str = "imports/wnacg"
    download_use_mock: bool = True
    download_api_domain: str = "www.wn07.ru"
    download_preview_batch_size: int = 10
    download_concurrency: int = 2
    download_speed_limit_kbps: int = 0
    download_cache_dir: str = "/data/cache"


class SettingsUpdate(BaseModel):
    gallery_root: str | None = None
    thumb_dir: str | None = None
    thumb_max_size: int | None = Field(default=None, ge=64, le=2000)
    watch_enabled: bool | None = None
    watch_debounce_seconds: int | None = Field(default=None, ge=1, le=60)
    log_level: LogLevel | None = None
    log_dir: str | None = None
    log_file_enabled: bool | None = None
    log_file_max_bytes: int | None = Field(default=None, ge=1024 * 1024, le=100 * 1024 * 1024)
    log_file_retention_days: int | None = Field(default=None, ge=1, le=365)
    recent_view_limit: int | None = Field(default=None, ge=1, le=100)
    recent_added_limit: int | None = Field(default=None, ge=1, le=100)
    download_proxy_enabled: bool | None = None
    download_proxy: str | None = None
    download_default_subdir: str | None = None
    download_use_mock: bool | None = None
    download_api_domain: str | None = None
    download_preview_batch_size: int | None = Field(default=None, ge=1, le=50)
    download_concurrency: int | None = Field(default=None, ge=1, le=10)
    download_speed_limit_kbps: int | None = Field(default=None, ge=0, le=102400)
    download_cache_dir: str | None = None


class SettingsSaveResponse(SettingsResponse):
    message: str | None = None
    needs_rescan: bool = False


class ThumbRebuildResponse(BaseModel):
    deleted: int
    message: str
