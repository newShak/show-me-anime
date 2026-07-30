"""扫描 runner 测试。"""

from PIL import Image

from app.services.scan_runner import run_scan


def _make_album(gallery, name: str):
    path = gallery / name
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (0, 128, 255)).save(path / "1.jpg", format="JPEG")


def test_run_scan_indexes_new_folder(gallery):
    _make_album(gallery, "watch-me")
    job = run_scan()
    assert job is not None
    assert job.added >= 1


def test_run_scan_skips_when_busy():
    from app.services import scan_runner

    scan_runner._lock.acquire()
    try:
        assert run_scan() is None
    finally:
        scan_runner._lock.release()
