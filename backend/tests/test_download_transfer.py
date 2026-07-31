"""断点续传工具测试。"""

import zipfile
from pathlib import Path

from app.services.download.transfer import (
    ZIP_NAME,
    is_job_resumable,
    parse_total_bytes,
    save_resume_meta,
    try_extract_or_none,
    validate_resume_file_key,
)


def test_parse_total_bytes():
    assert parse_total_bytes("bytes 0-999/5000", "1000", 0, 206) == 5000
    assert parse_total_bytes(None, "1000", 2000, 206) == 3000
    assert parse_total_bytes(None, "1000", 0, 200) == 1000


def test_is_job_resumable(tmp_path):
    cache = tmp_path / "job1"
    cache.mkdir()
    assert not is_job_resumable(cache)
    (cache / ZIP_NAME).write_bytes(b"partial")
    assert is_job_resumable(cache)


def test_validate_resume_file_key(tmp_path):
    cache = tmp_path / "job1"
    cache.mkdir()
    save_resume_meta(cache, {"file_key": "abc.zip"})
    assert validate_resume_file_key(cache, "abc.zip")
    assert not validate_resume_file_key(cache, "other.zip")


def test_speed_limiter_zero():
    from app.services.download.transfer import SpeedLimiter

    limiter = SpeedLimiter(0)
    limiter.wait(1024 * 1024)


def test_speed_limiter_waits(monkeypatch):
    from app.services.download.transfer import SpeedLimiter

    slept = []

    def fake_sleep(sec: float) -> None:
        slept.append(sec)

    monkeypatch.setattr("app.services.download.transfer.time.sleep", fake_sleep)
    limiter = SpeedLimiter(1024)
    limiter.wait(2048)
    assert len(slept) == 1
    assert slept[0] > 0


def test_try_extract_or_none(tmp_path):
    cache = tmp_path / "job1"
    cache.mkdir()
    zip_path = cache / ZIP_NAME
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("001.jpg", b"fake-image")
    assert try_extract_or_none(zip_path, cache) == 1
    assert (cache / "001.jpg").is_file()

    zip_path.write_bytes(b"not-a-zip")
    assert try_extract_or_none(zip_path, cache) is None
