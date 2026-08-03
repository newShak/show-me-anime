"""外站下载 API DTO。"""

from pydantic import BaseModel, Field


class DownloadSourceResponse(BaseModel):
    id: str
    name: str
    mock: bool = False


class RemoteAlbumResponse(BaseModel):
    source: str
    id: str
    title: str
    cover_url: str
    page_count: int | None = None
    category: str | None = None
    language: str | None = None
    tags: list[str] = []


class RemoteSearchResponse(BaseModel):
    items: list[RemoteAlbumResponse]
    total: int
    page: int
    page_size: int


class BrowseNavItemResponse(BaseModel):
    label: str
    cate_id: int | None = None
    children: list["BrowseNavItemResponse"] = []


class RemoteBrowseResponse(BaseModel):
    items: list[RemoteAlbumResponse]
    total: int
    page: int
    page_size: int
    cate_id: int | None = None
    title: str = "首頁"
    nav: list[BrowseNavItemResponse] = []


class RemoteDetailResponse(BaseModel):
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
    tags: list[str] = []
    default_target_rel_path: str
    default_parent_rel_path: str = "imports/wnacg"


class RemotePreviewBatchResponse(BaseModel):
    preview_urls: list[str]
    offset: int
    count: int
    total: int
    has_more: bool


class DownloadJobCreate(BaseModel):
    source: str = "wnacg"
    album_id: str
    title: str
    target_rel_path: str = Field(min_length=1)
    tag_ids: list[int] = []
    import_remote_tags: list[str] = []


class DownloadJobBatchItem(BaseModel):
    source: str = "wnacg"
    album_id: str
    title: str
    tag_ids: list[int] = []
    import_remote_tags: list[str] = []


class DownloadJobBatchCreate(BaseModel):
    items: list[DownloadJobBatchItem] = Field(min_length=1)
    parent_rel_path: str = ""
    tag_ids: list[int] = []


class DownloadJobResponse(BaseModel):
    id: str
    source: str
    album_id: str
    title: str
    target_rel_path: str
    status: str
    progress: int = 0
    message: str | None = None
    saved_files: int = 0
    skipped_files: int = 0
    target_existed: bool = False


class DownloadJobBatchResponse(BaseModel):
    jobs: list[DownloadJobResponse]


class DownloadCacheClearResponse(BaseModel):
    deleted: int
    message: str


class ProxyTestResponse(BaseModel):
    ok: bool
    message: str


class DownloadOptionsResponse(BaseModel):
    preview_batch_size: int
    concurrency: int


class DownloadRecordResponse(BaseModel):
    id: str
    source: str
    album_id: str
    title: str
    target_rel_path: str
    status: str
    progress: int = 0
    message: str | None = None
    saved_files: int = 0
    skipped_files: int = 0
    target_existed: bool = False
    size_bytes: int = 0
    created_at: float
    finished_at: float | None = None
    resumable: bool = False
    can_overwrite: bool = False


class DownloadRecordListResponse(BaseModel):
    items: list[DownloadRecordResponse]
    total: int
    page: int
    page_size: int
    page_total_bytes: int = 0
