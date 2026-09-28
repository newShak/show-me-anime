"""wnacg 适配器单元测试（网络 I/O 用 monkeypatch 拦掉）。"""

from pathlib import Path

import pytest

from app.services.download.wnacg import WnacgAdapter
from app.services.download.wnacg_parse import parse_download_page

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://www.wn07.ru"
SIGNED = "https://d1.wcdn.date/api/dl?sign=abc&expiry=123"


@pytest.fixture
def adapter(monkeypatch) -> WnacgAdapter:
    import app.services.download.wnacg as wnacg

    wnacg._effective_base_cache.clear()
    a = WnacgAdapter()
    monkeypatch.setattr(type(a), "use_mock", property(lambda self: False))
    monkeypatch.setattr(a, "_effective_base_url", lambda: BASE)
    monkeypatch.setattr(a, "_get_html", lambda path, **kw: (FIXTURES / "wnacg_download.html").read_text(encoding="utf-8"))
    return a


def test_resolve_download_prefers_signed_url(adapter, monkeypatch):
    monkeypatch.setattr(adapter, "_fetch_signed_download_url", lambda *a, **kw: SIGNED)
    target = adapter._live_resolve_download("3746")
    assert target.kind == "archive"
    assert target.urls == [SIGNED]
    assert target.filename == parse_download_page((FIXTURES / "wnacg_download.html").read_text(encoding="utf-8"))["file_name"]


def test_resolve_download_falls_back_to_backup_url(adapter, monkeypatch):
    def blocked(*a, **kw):
        raise ValueError("CDN 签名接口被 Cloudflare 拦截，请开启下载代理后重试")

    monkeypatch.setattr(adapter, "_fetch_signed_download_url", blocked)
    target = adapter._live_resolve_download("3746")
    assert target.kind == "archive"
    assert target.urls[0] == parse_download_page((FIXTURES / "wnacg_download.html").read_text(encoding="utf-8"))["backup_url"]
    assert target.referer == f"{BASE}/download-index-aid-3746.html"


def test_resolve_download_reraises_without_backup(adapter, monkeypatch):
    def blocked(*a, **kw):
        raise ValueError("CDN 签名接口被 Cloudflare 拦截，请开启下载代理后重试")

    monkeypatch.setattr(adapter, "_fetch_signed_download_url", blocked)
    monkeypatch.setattr(
        adapter,
        "_get_html",
        lambda path, **kw: """
        <script>
        const CONFIG = {
            WORKER_API: "https://d1.wcdn.date/api/generate-link",
            FILE_KEY: "down/1/test.zip",
            FILE_NAME: "test.zip"
        };
        </script>
        """,
    )
    with pytest.raises(ValueError, match="Cloudflare"):
        adapter._live_resolve_download("3746")
