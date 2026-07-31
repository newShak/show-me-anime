"""外站适配器基类。"""

from typing import Protocol

from app.services.download.types import DownloadTarget, RemoteDetail, RemoteSearchResult


class SiteAdapter(Protocol):
    source_id: str
    display_name: str

    def search(self, q: str, page: int = 1, page_size: int = 24) -> RemoteSearchResult: ...

    def get_detail(self, album_id: str) -> RemoteDetail: ...

    def resolve_download(self, album_id: str) -> DownloadTarget: ...

    def fetch_cover_bytes(self, album_id: str) -> tuple[bytes, str]: ...
