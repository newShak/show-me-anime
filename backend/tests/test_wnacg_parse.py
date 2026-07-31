"""wnacg HTML 解析测试。"""

from pathlib import Path

from app.services.download.wnacg_parse import abs_url, parse_detail, parse_detail_pagination, parse_download_page, parse_search_items, parse_search_total, PAGE_SIZE

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


def test_parse_albums_pagination_fixture():
    html = (FIXTURES / "wnacg_search.html").read_text(encoding="utf-8")
    from app.services.download.wnacg_parse import albums_page_path, parse_albums_pagination, parse_albums_total

    pag = parse_albums_pagination(html)
    assert pag["current_page"] >= 1
    assert pag["total_pages"] >= 1
    assert parse_albums_total(html) >= PAGE_SIZE
    assert albums_page_path(1) == "/albums-index-page-1.html"
    assert albums_page_path(2, 37) == "/albums-index-page-2-cate-37.html"
    assert albums_page_path(1, 37) == "/albums-index-cate-37.html"


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
