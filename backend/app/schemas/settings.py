"""配置相关 DTO。"""

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    gallery_root: str
    thumb_dir: str
    database_url: str
    thumb_max_size: int
    watch_enabled: bool
    watch_debounce_seconds: int
    album_list_cache_ttl: int
    host: str
    port: int
