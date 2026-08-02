"""wnacg 适配器：搜索/详情/封面解析，下载延后。"""

import hashlib
import io
import logging
import re
import threading
import time

from PIL import Image

from app.config import Settings, get_settings
from app.services.download.http_client import browser_post_json, download_client, generate_link_headers, is_cloudflare_challenge
from app.services.download.types import DownloadTarget, PreviewBatch, RemoteAlbum, RemoteBrowseResult, RemoteDetail, RemoteSearchResult, BrowseNavItem
from app.services.download.wnacg_parse import (
    PAGE_SIZE,
    albums_page_path,
    detail_page_path,
    normalize_domain,
    parse_albums_total,
    parse_detail,
    parse_detail_pagination,
    parse_detail_previews,
    parse_download_page,
    parse_search_items,
    parse_search_total,
)
from app.services.download.wnacg_nav import BROWSE_NAV, browse_title

logger = logging.getLogger(__name__)

SOURCE_ID = "wnacg"
DISPLAY_NAME = "WNA CG"
DEFAULT_DOMAIN = "www.wn07.ru"

# 搜索页已解析的封面 URL，避免重复拉详情页
_cover_url_cache: dict[str, str] = {}
_preview_url_cache: dict[str, list[str]] = {}
_preview_meta_cache: dict[str, dict[str, int]] = {}
_effective_base_cache: dict[str, str] = {}
# generate-link 必须串行，并发 POST 会被 CDN WAF 403
_link_sign_lock = threading.Lock()


def _cdn_url_flags(url: str) -> tuple[str, bool, bool]:
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    return parsed.netloc, "sign" in qs, "expiry" in qs


def _placeholder_cover(album_id: str, size: int = 320) -> bytes:
    seed = int(hashlib.md5(album_id.encode()).hexdigest()[:8], 16)
    r, g, b = (seed % 180 + 40, (seed // 3) % 180 + 40, (seed // 7) % 180 + 40)
    img = Image.new("RGB", (size, int(size * 1.35)), (r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _cover_api_path(album_id: str) -> str:
    return f"/api/download/cover?source={SOURCE_ID}&id={album_id}"


def _preview_api_path(album_id: str, index: int) -> str:
    return f"/api/download/preview?source={SOURCE_ID}&id={album_id}&n={index}"


class WnacgAdapter:
    source_id = SOURCE_ID
    display_name = DISPLAY_NAME

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def use_mock(self) -> bool:
        return self.settings.download_use_mock

    @property
    def domain(self) -> str:
        raw = getattr(self.settings, "download_api_domain", None) or DEFAULT_DOMAIN
        return normalize_domain(raw)

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}"

    def search(self, q: str, page: int = 1, page_size: int = 24) -> RemoteSearchResult:
        if self.use_mock:
            return self._mock_search(q, page, page_size)
        return self._live_search(q, page, page_size)

    def browse(self, cate_id: int | None = None, page: int = 1, page_size: int = 24) -> RemoteBrowseResult:
        if self.use_mock:
            return self._mock_browse(cate_id, page, page_size)
        return self._live_browse(cate_id, page, page_size)

    def get_detail(self, album_id: str) -> RemoteDetail:
        if self.use_mock:
            return self._mock_detail(album_id)
        return self._live_detail(album_id)

    def resolve_download(self, album_id: str) -> DownloadTarget:
        if self.use_mock:
            return DownloadTarget(kind="images", urls=[f"mock://{album_id}/{i}" for i in range(1, 4)])
        return self._live_resolve_download(album_id)

    def _live_resolve_download(self, album_id: str) -> DownloadTarget:
        referer_base = self._effective_base_url()
        download_page = f"{referer_base}/download-index-aid-{album_id}.html"
        html = self._get_html(f"/download-index-aid-{album_id}.html")
        cfg = parse_download_page(html)
        url = self._fetch_signed_download_url(
            album_id,
            cfg["worker_api"],
            cfg["file_key"],
            cfg["file_name"],
            download_page,
            referer_base,
        )
        cdn_host, signed, has_expiry = _cdn_url_flags(url)
        logger.info(
            "wnacg download aid=%s worker=%s cdn_host=%s signed=%s expiry=%s url=%s",
            album_id,
            cfg["worker_api"].split("/")[2] if "://" in cfg["worker_api"] else cfg["worker_api"],
            cdn_host,
            signed,
            has_expiry,
            url[:120],
        )
        return DownloadTarget(
            kind="archive",
            urls=[url],
            filename=cfg["file_name"],
            referer=download_page,
            file_key=cfg["file_key"],
        )

    def _fetch_signed_download_url(
        self,
        album_id: str,
        worker_api: str,
        file_key: str,
        file_name: str,
        referer: str,
        origin: str,
    ) -> str:
        headers = generate_link_headers(referer, origin)
        payload = {"file_key": file_key, "file_name": file_name}
        last_err = ""
        cf_blocked = False
        for attempt in range(3):
            try:
                with _link_sign_lock:
                    status, body, data = browser_post_json(
                        worker_api,
                        payload,
                        headers,
                        self.settings,
                    )
                if status == 200 and data and data.get("success") and data.get("url"):
                    return str(data["url"])
                if status == 200 and data:
                    last_err = str(data.get("msg") or "generate-link rejected")
                    logger.warning(
                        "generate-link rejected aid=%s worker=%s attempt=%s msg=%s",
                        album_id,
                        worker_api,
                        attempt + 1,
                        last_err,
                    )
                else:
                    last_err = f"HTTP {status}"
                    if is_cloudflare_challenge(body):
                        cf_blocked = True
                        last_err = "Cloudflare 拦截"
                    logger.warning(
                        "generate-link HTTP %s aid=%s worker=%s attempt=%s origin=%s referer=%s body=%s",
                        status,
                        album_id,
                        worker_api,
                        attempt + 1,
                        headers.get("Origin"),
                        referer,
                        body[:200],
                    )
            except Exception as exc:
                last_err = str(exc)
                logger.warning(
                    "generate-link error aid=%s worker=%s attempt=%s: %s",
                    album_id,
                    worker_api,
                    attempt + 1,
                    exc,
                )
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
        if cf_blocked:
            raise ValueError("CDN 签名接口被 Cloudflare 拦截，请开启下载代理后重试")
        raise ValueError(f"无法获取下载链接，请检查代理或稍后重试 ({last_err})")

    def fetch_cover_bytes(self, album_id: str) -> tuple[bytes, str]:
        if self.use_mock:
            return _placeholder_cover(album_id), "image/jpeg"
        cover_url = _cover_url_cache.get(album_id) or self._live_cover_url(album_id)
        referer = self._effective_base_url()
        with download_client(self.settings) as client:
            res = client.get(cover_url, headers={"Referer": f"{referer}/"})
            res.raise_for_status()
        media = res.headers.get("content-type") or "image/jpeg"
        return res.content, media.split(";")[0].strip()

    def fetch_preview_bytes(self, album_id: str, index: int) -> tuple[bytes, str]:
        if self.use_mock:
            return _placeholder_cover(f"{album_id}-{index}"), "image/jpeg"
        self._ensure_preview_cache(album_id, index + 1)
        urls = _preview_url_cache.get(album_id, [])
        if index < 0 or index >= len(urls):
            raise ValueError(f"preview index out of range: {index}")
        referer = self._effective_base_url()
        with download_client(self.settings) as client:
            res = client.get(urls[index], headers={"Referer": f"{referer}/"})
            res.raise_for_status()
        media = res.headers.get("content-type") or "image/jpeg"
        return res.content, media.split(";")[0].strip()

    def _preview_batch_size(self) -> int:
        return max(1, min(50, int(getattr(self.settings, "download_preview_batch_size", 10) or 10)))

    def get_preview_batch(self, album_id: str, offset: int = 0, limit: int | None = None) -> PreviewBatch:
        size = limit if limit is not None else self._preview_batch_size()
        if self.use_mock:
            return self._mock_preview_batch(album_id, offset, size)
        return self._live_preview_batch(album_id, offset, size)

    def _init_preview_cache(self, album_id: str) -> None:
        if album_id in _preview_meta_cache:
            return
        html = self._get_html(detail_page_path(album_id, 1))
        parsed = parse_detail(html, self.domain)
        pag = parse_detail_pagination(html)
        urls = list(parsed.get("preview_urls") or [])
        if not urls and parsed.get("cover_url"):
            urls = [str(parsed["cover_url"])]
        _preview_url_cache[album_id] = urls
        _preview_meta_cache[album_id] = {
            "site_page_fetched": 1,
            "total_site_pages": pag["total_pages"],
            "page_count": int(parsed["page_count"]) if parsed["page_count"] else len(urls),
        }
        cover = str(parsed.get("cover_url") or "")
        if cover:
            _cover_url_cache[album_id] = cover

    def _ensure_preview_cache(self, album_id: str, min_count: int) -> None:
        self._init_preview_cache(album_id)
        urls = _preview_url_cache.setdefault(album_id, [])
        meta = _preview_meta_cache[album_id]
        site_page = meta["site_page_fetched"]
        total_site_pages = meta["total_site_pages"]
        while len(urls) < min_count and site_page < total_site_pages:
            site_page += 1
            html = self._get_html(detail_page_path(album_id, site_page))
            batch = parse_detail_previews(html, self.domain)
            if not batch:
                break
            urls.extend(batch)
            meta["site_page_fetched"] = site_page

    def _preview_has_more(self, album_id: str, next_offset: int) -> bool:
        meta = _preview_meta_cache.get(album_id)
        urls = _preview_url_cache.get(album_id, [])
        if not meta:
            return False
        if len(urls) > next_offset:
            return True
        return meta["site_page_fetched"] < meta["total_site_pages"]

    def _live_preview_batch(self, album_id: str, offset: int, limit: int) -> PreviewBatch:
        need = offset + limit
        self._ensure_preview_cache(album_id, need)
        urls = _preview_url_cache.get(album_id, [])
        meta = _preview_meta_cache.get(album_id, {})
        batch = urls[offset : offset + limit]
        paths = [_preview_api_path(album_id, offset + i) for i in range(len(batch))]
        total = meta.get("page_count") or len(urls)
        return PreviewBatch(
            preview_urls=paths,
            offset=offset,
            count=len(paths),
            total=total,
            has_more=self._preview_has_more(album_id, offset + len(batch)),
        )

    def _effective_base_url(self) -> str:
        cached = _effective_base_cache.get(self.domain)
        if cached:
            return cached
        with download_client(self.settings) as client:
            res = client.get(f"{self.base_url}/", headers={"Referer": f"{self.base_url}/"})
            base = f"{res.url.scheme}://{res.url.host}"
        _effective_base_cache[self.domain] = base
        return base

    def _get_html(self, path: str, **kwargs) -> str:
        with download_client(self.settings) as client:
            headers = {"Referer": f"{self.base_url}/", **kwargs.pop("headers", {})}
            res = client.get(f"{self.base_url}{path}", headers=headers, **kwargs)
            res.raise_for_status()
            _effective_base_cache[self.domain] = f"{res.url.scheme}://{res.url.host}"
            return res.text

    def _live_cover_url(self, album_id: str) -> str:
        html = self._get_html(f"/photos-index-aid-{album_id}.html")
        parsed = parse_detail(html, self.domain)
        cover = str(parsed["cover_url"])
        if not cover:
            raise ValueError(f"cover not found for album {album_id}")
        return cover

    def _rows_to_albums(self, rows: list[dict], page_size: int) -> list[RemoteAlbum]:
        items: list[RemoteAlbum] = []
        for row in rows[:page_size]:
            album_id = str(row["id"])
            ext_cover = str(row["cover_url"]) if row.get("cover_url") else ""
            if ext_cover:
                _cover_url_cache[album_id] = ext_cover
            items.append(
                RemoteAlbum(
                    source=SOURCE_ID,
                    id=album_id,
                    title=str(row["title"]),
                    cover_url=_cover_api_path(album_id),
                    page_count=row["page_count"] if isinstance(row["page_count"], int) else None,
                    category=str(row["category"]) if row.get("category") else None,
                    language=str(row["language"]) if row.get("language") else None,
                    tags=[],
                )
            )
        return items

    def _nav_items(self) -> list[BrowseNavItem]:
        return [
            BrowseNavItem(label=i.label, cate_id=i.cate_id, children=[BrowseNavItem(label=c.label, cate_id=c.cate_id) for c in i.children])
            for i in BROWSE_NAV
        ]

    def _live_browse(self, cate_id: int | None, page: int, page_size: int) -> RemoteBrowseResult:
        path = albums_page_path(page, cate_id)
        logger.info("wnacg live browse domain=%s cate=%s page=%s path=%s", self.domain, cate_id, page, path)
        html = self._get_html(path)
        rows = parse_search_items(html, self.domain)
        total = parse_albums_total(html)
        items = self._rows_to_albums(rows, page_size)
        return RemoteBrowseResult(
            items=items,
            total=total,
            page=page,
            page_size=min(page_size, PAGE_SIZE),
            cate_id=cate_id,
            title=browse_title(cate_id),
            nav=self._nav_items(),
        )

    def _live_search(self, q: str, page: int, page_size: int) -> RemoteSearchResult:
        q = (q or "").strip()
        logger.info("wnacg live search domain=%s q=%s page=%s", self.domain, q, page)
        params = {"q": q, "syn": "yes", "f": "_all", "s": "create_time_DESC", "p": page}
        html = self._get_html("/search/index.php", params=params)
        rows = parse_search_items(html, self.domain)
        total = parse_search_total(html)
        items = self._rows_to_albums(rows, page_size)
        return RemoteSearchResult(
            items=items,
            total=total,
            page=page,
            page_size=min(page_size, PAGE_SIZE),
        )

    def _live_detail(self, album_id: str) -> RemoteDetail:
        html = self._get_html(detail_page_path(album_id, 1))
        parsed = parse_detail(html, self.domain)
        pag = parse_detail_pagination(html)
        urls = list(parsed.get("preview_urls") or [])
        if not urls and parsed.get("cover_url"):
            urls = [str(parsed["cover_url"])]
        _preview_url_cache[album_id] = urls
        page_count = int(parsed["page_count"]) if parsed["page_count"] else len(urls)
        _preview_meta_cache[album_id] = {
            "site_page_fetched": 1,
            "total_site_pages": pag["total_pages"],
            "page_count": page_count,
        }
        cover = str(parsed.get("cover_url") or "")
        if cover:
            _cover_url_cache[album_id] = cover
        batch = self._live_preview_batch(album_id, 0, self._preview_batch_size())
        cover_path = _cover_api_path(album_id)
        preview_paths = batch.preview_urls or [cover_path]
        return RemoteDetail(
            source=SOURCE_ID,
            id=album_id,
            title=str(parsed["title"]),
            page_count=page_count,
            cover_url=cover_path,
            preview_urls=preview_paths,
            preview_has_more=batch.has_more,
            preview_total=batch.total,
            category=str(parsed["category"]) if parsed.get("category") else None,
            language=str(parsed["language"]) if parsed.get("language") else None,
            tags=list(parsed["tags"]),
        )

    def _mock_browse(self, cate_id: int | None, page: int, page_size: int) -> RemoteBrowseResult:
        title = browse_title(cate_id)
        seed = cate_id or 0
        total = 120
        start = (page - 1) * page_size
        items: list[RemoteAlbum] = []
        for i in range(start, min(start + page_size, total)):
            album_id = str(20000 + seed * 1000 + i)
            items.append(
                RemoteAlbum(
                    source=SOURCE_ID,
                    id=album_id,
                    title=f"{title} · 示例相册 {i + 1}",
                    cover_url=_cover_api_path(album_id),
                    page_count=16 + (i % 20),
                    category=title.split(" · ")[0] if " · " in title else title,
                    language="漢化" if i % 2 == 0 else "日語",
                    tags=["mock"],
                )
            )
        return RemoteBrowseResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            cate_id=cate_id,
            title=title,
            nav=self._nav_items(),
        )

    def _mock_search(self, q: str, page: int, page_size: int) -> RemoteSearchResult:
        q = (q or "").strip() or "sample"
        total = 48
        start = (page - 1) * page_size
        items: list[RemoteAlbum] = []
        for i in range(start, min(start + page_size, total)):
            album_id = str(10000 + i)
            title = f"{q} · 示例相册 {i + 1}"
            items.append(
                RemoteAlbum(
                    source=SOURCE_ID,
                    id=album_id,
                    title=title,
                    cover_url=_cover_api_path(album_id),
                    page_count=20 + (i % 30),
                    category="示例分类",
                    language="漢化" if i % 2 == 0 else "日語",
                    tags=["mock"],
                )
            )
        return RemoteSearchResult(items=items, total=total, page=page, page_size=page_size)

    def _mock_detail(self, album_id: str) -> RemoteDetail:
        title = f"示例相册 {album_id}"
        pages = 24
        cover_path = _cover_api_path(album_id)
        batch = self._mock_preview_batch(album_id, 0, self._preview_batch_size())
        return RemoteDetail(
            source=SOURCE_ID,
            id=album_id,
            title=title,
            page_count=pages,
            cover_url=cover_path,
            preview_urls=batch.preview_urls or [cover_path],
            preview_has_more=batch.has_more,
            preview_total=batch.total,
            category="示例分类",
            language="漢化",
            tags=["mock"],
        )

    def _mock_preview_batch(self, album_id: str, offset: int, limit: int) -> PreviewBatch:
        total = 24
        end = min(offset + limit, total)
        paths = [_preview_api_path(album_id, i) for i in range(offset, end)]
        return PreviewBatch(
            preview_urls=paths,
            offset=offset,
            count=len(paths),
            total=total,
            has_more=end < total,
        )
