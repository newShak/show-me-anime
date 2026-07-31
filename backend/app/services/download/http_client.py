"""外站 HTTP 客户端（支持代理）。"""

import httpx

from app.config import Settings, get_settings
from app.services.download.wnacg_parse import normalize_domain

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CORS_API_HEADERS = {
    "Accept": "*/*",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}


def site_origin_headers(origin: str) -> dict[str, str]:
    """跨站 API / CDN 请求用的 Origin + Referer（与浏览器 download 页一致）。"""
    base = origin.rstrip("/")
    return {"Origin": base, "Referer": f"{base}/"}


def generate_link_headers(referer: str, origin: str) -> dict[str, str]:
    """generate-link 用最小请求头；勿带 sec-fetch，非浏览器 TLS 易被 CDN WAF 403。"""
    base = origin.rstrip("/")
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": base,
        "Referer": referer,
    }


def cdn_download_headers(referer_origin: str) -> dict[str, str]:
    return {**CORS_API_HEADERS, **site_origin_headers(referer_origin)}

DEFAULT_API_DOMAIN = "www.wn07.ru"


def api_domain(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    raw = getattr(settings, "download_api_domain", None) or DEFAULT_API_DOMAIN
    return normalize_domain(raw)


def api_base_url(settings: Settings | None = None) -> str:
    return f"https://{api_domain(settings)}"


def download_client(settings: Settings | None = None) -> httpx.Client:
    settings = settings or get_settings()
    proxy = settings.download_proxy if settings.download_proxy_enabled else None
    return httpx.Client(
        proxy=proxy or None,
        timeout=httpx.Timeout(300.0, connect=20.0),
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    )


def _download_proxy(settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    if settings.download_proxy_enabled and settings.download_proxy:
        return settings.download_proxy
    return None


def is_cloudflare_challenge(body: str) -> bool:
    text = (body or "").lower()
    return "just a moment" in text or "cf-browser-verification" in text


def browser_post_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    settings: Settings | None = None,
    *,
    timeout: float = 30.0,
) -> tuple[int, str, dict | None]:
    """Chrome TLS 指纹 POST，用于 Cloudflare 保护的 generate-link。"""
    from curl_cffi import requests as cf_requests

    proxy = _download_proxy(settings)
    proxies = {"http": proxy, "https": proxy} if proxy else None
    res = cf_requests.post(
        url,
        json=payload,
        headers=headers,
        impersonate="chrome",
        proxies=proxies,
        timeout=timeout,
    )
    data: dict | None = None
    if res.status_code == 200:
        try:
            parsed = res.json()
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            pass
    return res.status_code, res.text or "", data


def probe_proxy(settings: Settings | None = None, url: str | None = None) -> tuple[bool, str]:
    """测试能否访问 wnacg 镜像 API 域名。"""
    settings = settings or get_settings()
    base = api_base_url(settings)
    test_url = url or f"{base}/search/index.php?q=test&syn=yes&f=_all&p=1&s=create_time_DESC"
    try:
        with download_client(settings) as client:
            res = client.get(test_url, headers={"Referer": f"{base}/"})
            if res.status_code < 400:
                return True, f"{api_domain(settings)} HTTP {res.status_code}"
            if res.status_code == 403 and "Just a moment" in res.text:
                return False, f"{api_domain(settings)} 被 Cloudflare 拦截，请换镜像域名（如 www.wn07.ru）"
            return False, f"{api_domain(settings)} HTTP {res.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)
