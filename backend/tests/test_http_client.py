"""HTTP 客户端辅助测试。"""

from app.services.download.http_client import is_cloudflare_challenge


def test_is_cloudflare_challenge():
    assert is_cloudflare_challenge('<html><title>Just a moment...</title></html>')
    assert is_cloudflare_challenge("cf-browser-verification")
    assert not is_cloudflare_challenge('{"success": false}')


def test_browser_post_json_success(monkeypatch):
    from app.services.download import http_client
    import curl_cffi.requests as cf_requests

    class FakeResp:
        status_code = 200
        text = '{"success": true, "url": "https://d1.wcdn.date/download?sign=x"}'

        def json(self):
            return {"success": True, "url": "https://d1.wcdn.date/download?sign=x"}

    monkeypatch.setattr(cf_requests, "post", lambda *args, **kwargs: FakeResp())
    status, body, data = http_client.browser_post_json(
        "https://d1.wcdn.date/api/generate-link",
        {"file_key": "a", "file_name": "b.zip"},
        {"Origin": "https://www.wn08.cfd", "Referer": "https://www.wn08.cfd/x.html"},
    )
    assert status == 200
    assert data and data["url"].startswith("https://d1.wcdn.date/")
