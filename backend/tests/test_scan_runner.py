"""扫描 runner 测试。"""

from PIL import Image

from app.services.scan_runner import run_scan, run_scan_wait


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


def test_run_scan_wait_waits_for_lock(gallery):
    import threading

    from app.services import scan_runner

    _make_album(gallery, "wait-scan")
    scan_runner._lock.acquire()
    released = threading.Event()

    def release_later():
        import time

        time.sleep(0.3)
        scan_runner._lock.release()
        released.set()

    threading.Thread(target=release_later, daemon=True).start()
    job = run_scan_wait(source="test", changed_paths=["wait-scan"], timeout=5.0)
    assert released.is_set()
    assert job is not None
