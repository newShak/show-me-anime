"""僵死下载任务回收测试。"""

import time

from app.db.models import DownloadRecord
from app.db.session import SessionLocal, get_engine
from app.services.download.jobs import is_download_job_running, reconcile_stale_download_jobs


def test_reconcile_stale_running_download_on_records(client):
    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(
            DownloadRecord(
                id="stale-dl-1",
                source="wnacg",
                album_id="album-1",
                title="中断任务",
                target_rel_path="imports/stale",
                status="running",
                progress=5,
                message="准备下载",
                created_at=now - 3600,
            )
        )
        db.commit()

    res = client.get("/api/download/records", params={"page": 1, "pageSize": 10})
    assert res.status_code == 200
    item = next(r for r in res.json()["items"] if r["id"] == "stale-dl-1")
    assert item["status"] == "failed"
    assert item["finished_at"] is not None
    assert "中断" in (item["message"] or "")


def test_reconcile_keeps_active_download_job():
    from app.services.download.jobs import _lock, _running_ids

    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(
            DownloadRecord(
                id="active-dl-1",
                source="wnacg",
                album_id="album-2",
                title="进行中",
                target_rel_path="imports/active",
                status="running",
                progress=50,
                message="下载压缩包",
                created_at=now - 60,
            )
        )
        db.commit()

        with _lock:
            _running_ids.add("active-dl-1")
        try:
            count = reconcile_stale_download_jobs(db)
            assert count == 0
            row = db.get(DownloadRecord, "active-dl-1")
            assert row.status == "running"
            assert is_download_job_running("active-dl-1")
        finally:
            with _lock:
                _running_ids.discard("active-dl-1")

        db.delete(db.get(DownloadRecord, "active-dl-1"))
        db.commit()


def test_reconcile_keeps_queued_pending_job():
    """排队等信号量的 pending 任务不应被误判为僵死。"""
    from app.services.download.jobs import _lock, _running_ids

    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(
            DownloadRecord(
                id="queued-dl-1",
                source="wnacg",
                album_id="album-q",
                title="排队中",
                target_rel_path="imports/queued",
                status="pending",
                progress=0,
                message="",
                created_at=now,
            )
        )
        db.commit()

        with _lock:
            _running_ids.add("queued-dl-1")
        try:
            count = reconcile_stale_download_jobs(db)
            assert count == 0
            row = db.get(DownloadRecord, "queued-dl-1")
            assert row.status == "pending"
            assert is_download_job_running("queued-dl-1")
        finally:
            with _lock:
                _running_ids.discard("queued-dl-1")

        db.delete(db.get(DownloadRecord, "queued-dl-1"))
        db.commit()


def test_reconcile_stale_marks_resumable(client):
    from app.config import get_settings

    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(
            DownloadRecord(
                id="stale-resume",
                source="wnacg",
                album_id="album-3",
                title="可续传",
                target_rel_path="imports/resume",
                status="running",
                progress=20,
                created_at=now - 120,
            )
        )
        db.commit()

    cache = get_settings().download_cache_dir / "stale-resume"
    cache.mkdir(parents=True)
    (cache / "_download.zip").write_bytes(b"partial")

    res = client.get("/api/download/records", params={"page": 1, "pageSize": 20})
    item = next(r for r in res.json()["items"] if r["id"] == "stale-resume")
    assert item["status"] == "failed"
    assert item["resumable"] is True
    assert "续传" in (item["message"] or "")
