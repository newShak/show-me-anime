"""外站下载数据结构。"""

from dataclasses import dataclass, field
from typing import Literal


class DownloadCancelled(Exception):
    """用户主动取消下载。"""


@dataclass
class RemoteAlbum:
    source: str
    id: str
    title: str
    cover_url: str
    page_count: int | None = None
    category: str | None = None
    language: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class RemoteSearchResult:
    items: list[RemoteAlbum]
    total: int
    page: int
    page_size: int


@dataclass
class BrowseNavItem:
    label: str
    cate_id: int | None = None
    children: list["BrowseNavItem"] = field(default_factory=list)


@dataclass
class RemoteBrowseResult:
    items: list[RemoteAlbum]
    total: int
    page: int
    page_size: int
    cate_id: int | None = None
    title: str = "首頁"
    nav: list[BrowseNavItem] = field(default_factory=list)


@dataclass
class RemoteDetail:
    source: str
    id: str
    title: str
    page_count: int
    cover_url: str
    preview_urls: list[str]
    preview_has_more: bool = False
    preview_total: int = 0
    category: str | None = None
    language: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class PreviewBatch:
    preview_urls: list[str]
    offset: int
    count: int
    total: int
    has_more: bool


@dataclass
class DownloadTarget:
    kind: Literal["images", "archive"]
    urls: list[str]
    filename: str | None = None
    referer: str | None = None
    file_key: str | None = None


@dataclass
class DownloadJobState:
    id: str
    source: str
    album_id: str
    title: str
    target_rel_path: str
    status: Literal["pending", "running", "done", "failed"]
    progress: int = 0
    message: str | None = None
    saved_files: int = 0
    skipped_files: int = 0
    target_existed: bool = False
    tag_ids: list[int] = field(default_factory=list)
    import_remote_tags: list[str] = field(default_factory=list)
