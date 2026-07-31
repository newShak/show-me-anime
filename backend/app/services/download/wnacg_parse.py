"""wnacg HTML 解析（不含 imglist 下载）。"""

import html as html_lib
import re

from app.services.download.wnacg_cate import cate_info, infer_language_from_title, parse_cate_id

PAGE_SIZE = 24
PREVIEW_BATCH_SIZE = 10

_ITEM_RE = re.compile(r'<li class="li gallary_item">(.*?)</li>', re.DOTALL | re.IGNORECASE)
_AID_RE = re.compile(r"/photos-index-aid-(\d+)\.html")
_PAGE_COUNT_RE = re.compile(r"(\d+)\s*張圖片")
_TOTAL_RE = re.compile(
    r"大約有<b>\s*([\d,]+)\s*</b>項符合查詢結果",
    re.DOTALL,
)
_TITLE_RE = re.compile(r'<h2[^>]*>(.*?)</h2>', re.DOTALL | re.IGNORECASE)
_COVER_RE = re.compile(
    r'class="asTBcell uwthumb"[^>]*>.*?<img[^>]+src="([^"]+)"',
    re.DOTALL | re.IGNORECASE,
)
_PAGES_RE = re.compile(r"頁數：\s*(\d+)\s*P")
_CATEGORY_RE = re.compile(r"分類：\s*([^<]+)")
_TAG_RE = re.compile(r'<a class="tagshow"[^>]*>([^<]+)</a>', re.IGNORECASE)
_DOWNLOAD_CONFIG_RE = re.compile(
    r'WORKER_API:\s*"([^"]+)"[\s\S]*?FILE_KEY:\s*"([^"]+)"[\s\S]*?FILE_NAME:\s*"([^"]+)"',
    re.IGNORECASE,
)
_BACKUP_ZIP_RE = re.compile(r'href="(//dl[^"]+/down/[^"]+\.zip[^"]*)"', re.IGNORECASE)


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    domain = re.sub(r"^https?://", "", domain, flags=re.I).strip("/")
    return domain or "www.wn07.ru"


def abs_url(domain: str, src: str) -> str:
    src = html_lib.unescape(src.strip())
    if re.match(r"^/+[^/]", src):
        return "https://" + src.lstrip("/")
    if src.startswith("http://") or src.startswith("https://"):
        return src
    if src.startswith("/"):
        return f"https://{domain}{src}"
    return f"https://{domain}/{src.lstrip('/')}"


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html_lib.unescape(text).strip()


def parse_search_items(html: str, domain: str) -> list[dict[str, str | int | None]]:
    items: list[dict[str, str | int | None]] = []
    seen: set[str] = set()
    for block in _ITEM_RE.findall(html):
        m_aid = _AID_RE.search(block)
        if not m_aid:
            continue
        album_id = m_aid.group(1)
        if album_id in seen:
            continue
        seen.add(album_id)

        m_title = re.search(
            r'class="title">\s*<a[^>]+title="([^"]*)"[^>]*>(.*?)</a>',
            block,
            re.DOTALL | re.IGNORECASE,
        )
        title = _strip_html(m_title.group(2)) if m_title else f"album-{album_id}"
        if m_title and m_title.group(1).strip():
            title = _strip_html(m_title.group(1))

        m_img = re.search(r'\ssrc="(//[^"]+)"', block, re.I)
        if not m_img:
            m_img = re.search(r'\ssrc="(/[^"]+)"', block, re.I)
        cover_url = abs_url(domain, m_img.group(1)) if m_img else ""

        page_count: int | None = None
        m_pages = _PAGE_COUNT_RE.search(block)
        if m_pages:
            page_count = int(m_pages.group(1))

        cate_id = parse_cate_id(block)
        category, language = cate_info(cate_id)

        items.append(
            {
                "id": album_id,
                "title": title,
                "cover_url": cover_url,
                "page_count": page_count,
                "category": category,
                "language": language,
            }
        )
    return items


def parse_search_total(html: str) -> int:
    m = _TOTAL_RE.search(html)
    if m:
        return int(m.group(1).replace(",", ""))
    ids = _AID_RE.findall(html)
    return len(set(ids))


def albums_page_path(page: int = 1, cate_id: int | None = None) -> str:
    if cate_id is None:
        return f"/albums-index-page-{max(1, page)}.html"
    if page <= 1:
        return f"/albums-index-cate-{cate_id}.html"
    return f"/albums-index-page-{page}-cate-{cate_id}.html"


def parse_albums_pagination(html: str) -> dict[str, int]:
    pages = [1]
    for m in re.finditer(r"/albums-index-page-(\d+)(?:-cate-\d+)?\.html", html, re.I):
        pages.append(int(m.group(1)))
    total_pages = max(pages) if pages else 1
    current = 1
    m = re.search(r'<span class="thispage">(\d+)</span>', html, re.I)
    if m:
        current = int(m.group(1))
    return {"current_page": current, "total_pages": total_pages}


def parse_albums_total(html: str) -> int:
    pag = parse_albums_pagination(html)
    return pag["total_pages"] * PAGE_SIZE


def detail_page_path(album_id: str, page: int = 1) -> str:
    if page <= 1:
        return f"/photos-index-aid-{album_id}.html"
    return f"/photos-index-page-{page}-aid-{album_id}.html"


def parse_detail_pagination(html: str) -> dict[str, int]:
    pages = [1]
    for m in re.finditer(r"/photos-index-page-(\d+)-aid-", html, re.I):
        pages.append(int(m.group(1)))
    total_pages = max(pages) if pages else 1
    current = 1
    m = re.search(r'<span class="thispage">(\d+)</span>', html, re.I)
    if m:
        current = int(m.group(1))
    return {"current_page": current, "total_pages": total_pages}


def parse_detail(html: str, domain: str) -> dict[str, str | int | list[str]]:
    m_title = _TITLE_RE.search(html)
    title = _strip_html(m_title.group(1)) if m_title else "unknown"

    m_cover = _COVER_RE.search(html)
    if not m_cover:
        m_cover = re.search(
            r'class="asTBcell uwthumb"[^>]*>.*?<img[^>]*\ssrc="(//[^"]+)"',
            html,
            re.DOTALL | re.IGNORECASE,
        )
    cover_url = abs_url(domain, m_cover.group(1)) if m_cover else ""

    page_count = 0
    m_pages = _PAGES_RE.search(html)
    if m_pages:
        page_count = int(m_pages.group(1))

    category: str | None = None
    m_cat = _CATEGORY_RE.search(html)
    if m_cat:
        category = html_lib.unescape(m_cat.group(1).strip())

    cate_id = parse_cate_id(html)
    cate_category, language = cate_info(cate_id)
    if cate_category:
        category = cate_category
    if not language:
        language = infer_language_from_title(title)

    tags = [html_lib.unescape(t.strip()) for t in _TAG_RE.findall(html) if t.strip()]
    preview_urls = parse_detail_previews(html, domain)
    return {
        "title": title,
        "cover_url": cover_url,
        "page_count": page_count,
        "category": category,
        "language": language,
        "tags": tags,
        "preview_urls": preview_urls,
    }


def parse_detail_previews(html: str, domain: str) -> list[str]:
    """解析详情页当前页的缩略图（gallary_wrap tb 区域，非 imglist）。"""
    urls: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'<div class="pic_box tb">.*?<img[^>]*\ssrc="(//[^"]+)"',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        url = abs_url(domain, m.group(1))
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def parse_download_page(html: str) -> dict[str, str]:
    """解析 download-index 页中的 CONFIG 与备用下载链。"""
    m = _DOWNLOAD_CONFIG_RE.search(html)
    if not m:
        raise ValueError("download page missing CONFIG")
    worker_api, file_key, file_name = m.group(1), m.group(2), m.group(3)
    backup_url = ""
    m_backup = _BACKUP_ZIP_RE.search(html)
    if m_backup:
        backup_url = abs_url("", m_backup.group(1))
    elif file_key:
        backup_url = f"https://dl1.wn01.download/{file_key.lstrip('/')}"
    return {
        "worker_api": worker_api,
        "file_key": file_key,
        "file_name": file_name,
        "backup_url": backup_url,
    }
