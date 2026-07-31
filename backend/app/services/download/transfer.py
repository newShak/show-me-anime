"""支持 Range 的断点续传下载。"""

import json
import logging
import re
import time
import zipfile
from collections.abc import Callable
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

RESUME_META = ".resume.json"
ZIP_NAME = "_download.zip"
_CHUNK = 256 * 1024


class SpeedLimiter:
    """按 KB/s 限速，0 表示不限速。"""

    __slots__ = ("_bps", "_bytes", "_t0")

    def __init__(self, kbps: int):
        self._bps = kbps * 1024 if kbps > 0 else 0
        self._bytes = 0
        self._t0 = time.monotonic()

    def wait(self, nbytes: int) -> None:
        if self._bps <= 0 or nbytes <= 0:
            return
        self._bytes += nbytes
        need = self._bytes / self._bps
        spent = time.monotonic() - self._t0
        if need > spent:
            time.sleep(need - spent)


def parse_total_bytes(content_range: str | None, content_length: str | None, partial: int, status: int) -> int | None:
    if content_range:
        m = re.match(r"bytes \d+-\d+/(\d+)", content_range)
        if m:
            return int(m.group(1))
    if content_length:
        size = int(content_length)
        if status == 206:
            return partial + size
        return size
    return None


def save_resume_meta(cache_dir: Path, data: dict) -> None:
    (cache_dir / RESUME_META).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_resume_meta(cache_dir: Path) -> dict | None:
    path = cache_dir / RESUME_META
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def clear_resume_meta(cache_dir: Path) -> None:
    (cache_dir / RESUME_META).unlink(missing_ok=True)


def is_job_resumable(cache_dir: Path) -> bool:
    zip_path = cache_dir / ZIP_NAME
    return zip_path.is_file() and zip_path.stat().st_size > 0


def validate_resume_file_key(cache_dir: Path, file_key: str | None) -> bool:
    if not file_key:
        return True
    meta = load_resume_meta(cache_dir)
    if not meta or not meta.get("file_key"):
        return True
    return meta["file_key"] == file_key


def reset_partial_download(cache_dir: Path) -> None:
    (cache_dir / ZIP_NAME).unlink(missing_ok=True)
    clear_resume_meta(cache_dir)


def download_file_resumable(
    client: httpx.Client,
    url: str,
    referer: str | None,
    dest: Path,
    file_key: str | None,
    on_progress: Callable[[int, int | None], None] | None = None,
    speed_limit_kbps: int = 0,
) -> int:
    """下载到 dest，支持断点续传。返回最终文件大小。"""
    limiter = SpeedLimiter(speed_limit_kbps)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.stat().st_size if dest.is_file() else 0

    if partial > 0 and not validate_resume_file_key(dest.parent, file_key):
        logger.info("resume file_key mismatch, restart download")
        reset_partial_download(dest.parent)
        partial = 0

    headers: dict[str, str] = {}
    if referer:
        headers["Referer"] = referer
    if partial > 0:
        headers["Range"] = f"bytes={partial}-"

    with client.stream("GET", url, headers=headers, follow_redirects=True) as res:
        if partial > 0 and res.status_code in {416, 404}:
            reset_partial_download(dest.parent)
            return download_file_resumable(
                client, url, referer, dest, file_key, on_progress, speed_limit_kbps
            )

        if partial > 0 and res.status_code == 200:
            logger.info("server ignored Range, restart download")
            reset_partial_download(dest.parent)
            partial = 0

        mode = "ab" if res.status_code == 206 and partial > 0 else "wb"
        if mode == "wb" and dest.is_file():
            dest.unlink()

        total = parse_total_bytes(
            res.headers.get("content-range"),
            res.headers.get("content-length"),
            partial,
            res.status_code,
        )
        res.raise_for_status()
        done = partial if mode == "ab" else 0

        with dest.open(mode) as f:
            for chunk in res.iter_bytes(chunk_size=_CHUNK):
                limiter.wait(len(chunk))
                f.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
                if done % (_CHUNK * 8) < _CHUNK:
                    save_resume_meta(
                        dest.parent,
                        {
                            "url": url,
                            "referer": referer,
                            "file_key": file_key,
                            "downloaded": done,
                            "total": total,
                        },
                    )

    save_resume_meta(
        dest.parent,
        {"url": url, "referer": referer, "file_key": file_key, "downloaded": done, "total": total or done},
    )
    return done


def extract_zip_to_dir(zip_path: Path, dest_dir: Path) -> int:
    saved = 0
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            base = Path(name).name
            if not base or base.startswith("."):
                continue
            out = dest_dir / base
            with zf.open(name) as src, out.open("wb") as dst:
                dst.write(src.read())
            saved += 1
    return saved


def try_extract_or_none(zip_path: Path, dest_dir: Path) -> int | None:
    if not zip_path.is_file() or not zipfile.is_zipfile(zip_path):
        return None
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if zf.testzip() is not None:
                return None
        return extract_zip_to_dir(zip_path, dest_dir)
    except (zipfile.BadZipFile, OSError):
        return None
