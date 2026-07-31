"""应用配置：支持 config.yaml、.env、data/settings.json 多层覆盖。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GALLERY_ROOT = PROJECT_ROOT / "gallery"
DEFAULT_THUMB_DIR = PROJECT_ROOT / "data" / "thumbs"
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'data' / 'gallery.db').as_posix()}"
SETTINGS_JSON = PROJECT_ROOT / "data" / "settings.json"
CONFIG_YAML = PROJECT_ROOT / "config.yaml"


class Settings(BaseSettings):
    """运行时配置。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gallery_root: Path = Field(default=DEFAULT_GALLERY_ROOT)
    thumb_dir: Path = Field(default=DEFAULT_THUMB_DIR)
    database_url: str = Field(default=DEFAULT_DATABASE_URL)
    thumb_max_size: int = Field(default=400)
    watch_enabled: bool = Field(default=True)
    watch_debounce_seconds: int = Field(default=3)
    album_list_cache_ttl: int = Field(default=300)
    log_level: str = Field(default="INFO")
    recent_view_limit: int = Field(default=20, ge=1, le=100)
    recent_added_limit: int = Field(default=20, ge=1, le=100)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    download_proxy_enabled: bool = Field(default=False)
    download_proxy: str | None = Field(default=None)
    download_default_subdir: str = Field(default="imports/wnacg")
    download_use_mock: bool = Field(default=True)
    download_api_domain: str = Field(default="www.wn07.ru")
    download_preview_batch_size: int = Field(default=10, ge=1, le=50)
    download_concurrency: int = Field(default=2, ge=1, le=10)
    download_speed_limit_kbps: int = Field(default=0, ge=0, le=102400)
    download_cache_dir: Path = Field(default=Path("/data/cache"))

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        from app.logging_config import normalize_log_level

        return normalize_log_level(value)

    def resolve_paths(self) -> None:
        """相对路径转绝对路径，并确保必要目录存在。"""
        self.gallery_root = _to_abs(self.gallery_root)
        self.thumb_dir = _to_abs(self.thumb_dir)
        self.download_cache_dir = _to_abs(self.download_cache_dir)
        if self.gallery_root.exists() and not self.gallery_root.is_dir():
            raise ValueError(f"画廊根目录不可用: {self.gallery_root}")
        if self.thumb_dir.exists() and not self.thumb_dir.is_dir():
            raise ValueError(f"缩略图目录不可用: {self.thumb_dir}")
        self.gallery_root.mkdir(parents=True, exist_ok=True)
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.download_cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.gallery_root.is_dir():
            raise ValueError(f"画廊根目录不可用: {self.gallery_root}")
        if not self.thumb_dir.is_dir():
            raise ValueError(f"缩略图目录不可用: {self.thumb_dir}")

    def as_public_dict(self) -> dict[str, Any]:
        """供 API 返回的公开配置。"""
        return {
            "gallery_root": str(self.gallery_root),
            "thumb_dir": str(self.thumb_dir),
            "database_url": self.database_url,
            "thumb_max_size": self.thumb_max_size,
            "watch_enabled": self.watch_enabled,
            "watch_debounce_seconds": self.watch_debounce_seconds,
            "album_list_cache_ttl": self.album_list_cache_ttl,
            "log_level": self.log_level.upper(),
            "recent_view_limit": self.recent_view_limit,
            "recent_added_limit": self.recent_added_limit,
            "host": self.host,
            "port": self.port,
            "download_proxy_enabled": self.download_proxy_enabled,
            "download_proxy": self.download_proxy or "",
            "download_default_subdir": self.download_default_subdir,
            "download_use_mock": self.download_use_mock,
            "download_api_domain": self.download_api_domain,
            "download_preview_batch_size": self.download_preview_batch_size,
            "download_concurrency": self.download_concurrency,
            "download_speed_limit_kbps": self.download_speed_limit_kbps,
            "download_cache_dir": str(self.download_cache_dir),
        }


def _to_abs(path: Path | str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def _load_yaml_overrides() -> dict[str, Any]:
    if not CONFIG_YAML.exists():
        return {}
    data = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if v is not None}


def _load_json_overrides() -> dict[str, Any]:
    if not SETTINGS_JSON.exists():
        return {}
    data = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if v is not None}


@lru_cache
def get_settings() -> Settings:
    """加载并缓存配置。优先级：settings.json > .env > config.yaml > 默认值。"""
    settings = Settings(**_load_yaml_overrides())
    json_overrides = _load_json_overrides()
    if json_overrides:
        settings = settings.model_copy(update=json_overrides)
    settings.resolve_paths()
    return settings


def reload_settings() -> Settings:
    """清除缓存并重新加载（测试或管理页改配置后使用）。"""
    get_settings.cache_clear()
    return get_settings()


def update_settings_json(updates: dict[str, Any]) -> Settings:
    """合并写入 data/settings.json 并重新加载。"""
    current = _load_json_overrides()
    merged = {**current, **{k: v for k, v in updates.items() if v is not None}}
    get_settings.cache_clear()
    try:
        candidate = Settings(**{**_load_yaml_overrides(), **merged})
        candidate.resolve_paths()
    except ValueError:
        get_settings.cache_clear()
        get_settings()
        raise
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_JSON.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return reload_settings()
