"""wnacg HTML 解析测试。"""

import json
from pathlib import Path

from app.services.download.wnacg_parse import (
    abs_url,
    chapters_api_path,
    parse_chapters_payload,
    parse_detail,
    parse_detail_pagination,
    parse_download_page,
    parse_search_items,
    parse_search_total,
    PAGE_SIZE,
)

FIXTURES = Path(__file__).parent / "fixtures"
DOMAIN = "www.wn07.ru"


def test_parse_search_fixture():
    html = (FIXTURES / "wnacg_search.html").read_text(encoding="utf-8")
    items = parse_search_items(html, DOMAIN)
    assert len(items) >= 20
    assert items[0]["id"]
    assert items[0]["title"]
    assert str(items[0]["cover_url"]).startswith("https://")

    han = next(i for i in items if i.get("language") == "漢化")
    assert han.get("category")

    total = parse_search_total(html)
    assert total > len(items)


def test_cate_info():
    from app.services.download.wnacg_cate import cate_info

    assert cate_info(10) == ("雜誌&短篇", "漢化")
    assert cate_info(37) == ("AI&圖集", None)


def test_abs_url_protocol_relative_slashes():
    assert abs_url("www.wn07.ru", "//t4.wnacgimg.date/x.webp") == "https://t4.wnacgimg.date/x.webp"
    assert (
        abs_url("www.wn07.ru", "////t4.wnacgimg.date/x.webp")
        == "https://t4.wnacgimg.date/x.webp"
    )


def test_parse_download_fixture():
    html = (FIXTURES / "wnacg_download.html").read_text(encoding="utf-8")
    cfg = parse_download_page(html)
    assert cfg["file_key"].endswith(".zip")
    assert cfg["file_name"].endswith(".zip")
    assert cfg["worker_api"].startswith("https://")
    assert cfg["backup_url"].startswith("https://dl")


def test_parse_download_no_synthetic_backup():
    html = """
    <script>
    const CONFIG = {
        WORKER_API: "https://d1.wcdn.date/api/generate-link",
        FILE_KEY: "down/1/test.zip",
        FILE_NAME: "test.zip"
    };
    </script>
    """
    cfg = parse_download_page(html)
    assert cfg["backup_url"] == ""


def test_parse_albums_pagination_fixture():
    html = (FIXTURES / "wnacg_search.html").read_text(encoding="utf-8")
    from app.services.download.wnacg_parse import (
        albums_page_path,
        parse_albums_pagination,
        parse_albums_total,
        tag_albums_page_path,
    )

    pag = parse_albums_pagination(html)
    assert pag["current_page"] >= 1
    assert pag["total_pages"] >= 1
    assert parse_albums_total(html) >= PAGE_SIZE
    assert albums_page_path(1) == "/albums-index-page-1.html"
    assert albums_page_path(2, 37) == "/albums-index-page-2-cate-37.html"
    assert albums_page_path(1, 37) == "/albums-index-cate-37.html"
    assert tag_albums_page_path("無修正") == "/albums-index-tag-%E7%84%A1%E4%BF%AE%E6%AD%A3.html"
    assert tag_albums_page_path("卡莉奧斯特蘿", 2) == (
        "/albums-index-page-2-tag-%E5%8D%A1%E8%8E%89%E5%A5%A7%E6%96%AF%E7%89%B9%E8%98%BF.html"
    )


def test_parse_detail_fixture():
    html = (FIXTURES / "wnacg_detail.html").read_text(encoding="utf-8")
    detail = parse_detail(html, DOMAIN)
    assert detail["title"]
    assert str(detail["cover_url"]).startswith("https://")
    assert detail["page_count"] > 0
    assert isinstance(detail["tags"], list)
    previews = detail["preview_urls"]
    assert len(previews) >= 10
    assert all(str(u).startswith("https://") for u in previews)


def test_parse_detail_pagination_fixture():
    html = (FIXTURES / "wnacg_detail.html").read_text(encoding="utf-8")
    pag = parse_detail_pagination(html)
    assert pag["current_page"] == 1
    assert pag["total_pages"] >= 5


def test_parse_detail_fixture_is_not_series():
    html = (FIXTURES / "wnacg_detail.html").read_text(encoding="utf-8")
    detail = parse_detail(html, DOMAIN)
    assert detail["is_series"] is False
    assert detail["chapter_count"] == 0


def test_parse_series_detail_fixture():
    """合集页没有页数与预览区，取而代之的是章节目录。"""
    html = (FIXTURES / "wnacg_series_detail.html").read_text(encoding="utf-8")
    detail = parse_detail(html, DOMAIN)
    assert detail["is_series"] is True
    assert detail["chapter_count"] == 9
    assert detail["title"] == "[いぶろｰ｡] 不起眼女孩其實意外地色氣滿滿"
    assert detail["page_count"] == 0
    assert detail["preview_urls"] == []
    assert str(detail["cover_url"]).startswith("https://")


def test_parse_series_tags_exclude_chapter_links():
    """章节目录沿用站内 tagshow 样式，不能被当成标签。"""
    html = (FIXTURES / "wnacg_series_detail.html").read_text(encoding="utf-8")
    tags = parse_detail(html, DOMAIN)["tags"]
    assert "無修正" in tags
    assert "いぶろｰ｡" in tags
    assert not any(t.startswith("第") and "話" in t for t in tags)
    assert len(tags) == 11


def test_chapters_api_path():
    assert chapters_api_path("389535", 1) == "/?ctl=download&act=chapters&sid=389535&page=1"
    assert chapters_api_path("389535", 3) == "/?ctl=download&act=chapters&sid=389535&page=3"


def test_parse_chapters_payload_fixture():
    data = json.loads((FIXTURES / "wnacg_series_chapters.json").read_text(encoding="utf-8"))
    chapters, total = parse_chapters_payload(data)
    assert total == 9
    assert len(chapters) == 9
    assert chapters[0] == {
        "id": "141105",
        "index": 1,
        "name": "[いぶろｰ｡]不起眼女孩其實意外地色氣滿滿 1-18話",
        "page_count": 450,
    }
    assert chapters[-1]["id"] == "389546"
    assert chapters[-1]["index"] == 9
    assert chapters[-1]["page_count"] == 200


def test_parse_chapters_payload_ignores_junk_rows():
    data = {
        "code": 0,
        "total": 2,
        "page": 1,
        "limit": 30,
        "list": [
            {"id": 0, "idx": 1, "name": "bad"},
            "not-a-dict",
            {"id": 42, "idx": 2, "name": "ok", "pages": 12},
        ],
    }
    chapters, total = parse_chapters_payload(data)
    assert total == 2
    assert chapters == [{"id": "42", "index": 2, "name": "ok", "page_count": 12}]


def test_parse_chapters_payload_rejects_error_code():
    import pytest

    with pytest.raises(ValueError):
        parse_chapters_payload({"code": 1, "msg": "nope"})

