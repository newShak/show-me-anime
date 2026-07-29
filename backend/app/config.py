"""应用配置：支持 config.yaml、.env、data/settings.json 多层覆盖。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
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
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    def resolve_paths(self) -> None:
        """相对路径转绝对路径，并确保必要目录存在。"""
        self.gallery_root = _to_abs(self.gallery_root)
        self.thumb_dir = _to_abs(self.thumb_dir)
        self.gallery_root.mkdir(parents=True, exist_ok=True)
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        if not self.gallery_root.is_dir():
            raise ValueError(f"画廊根目录不可用: {self.gallery_root}")
        if not self.thumb_dir.exists() or not Path(self.thumb_dir).is_dir():
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
            "host": self.host,
            "port": self.port,
        }


def _to_abs(path: Path) -> Path:
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


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
