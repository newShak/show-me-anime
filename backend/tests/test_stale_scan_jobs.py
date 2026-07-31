"""僵死扫描任务回收测试。"""

import time

from app.constants import SCAN_INTERRUPTED, SCAN_RUNNING
from app.db.models import ScanJob
from app.db.session import SessionLocal, get_engine
from app.services.scan_runner import reconcile_stale_scan_jobs


def test_reconcile_stale_running_jobs_on_list(client):
    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(
            ScanJob(
                status=SCAN_RUNNING,
                source="api",
                mode="incremental",
                started_at=now - 3600,
            )
        )
        db.commit()

    res = client.get("/api/tasks", params={"page": 1, "pageSize": 10})
    assert res.status_code == 200
    scan = next(item for item in res.json()["items"] if item["task_type"] == "scan")
    assert scan["status"] == SCAN_INTERRUPTED
    assert scan["finished_at"] is not None
    assert "中断" in (scan["message"] or "")


def test_reconcile_keeps_active_running_job():
    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        old = ScanJob(
            status=SCAN_RUNNING,
            source="api",
            mode="incremental",
            started_at=now - 7200,
        )
        current = ScanJob(
            status=SCAN_RUNNING,
            source="api",
            mode="full",
            started_at=now - 60,
        )
        db.add(old)
        db.add(current)
        db.commit()
        old_id, current_id = old.id, current.id

        from app.services.scan_runner import _lock

        _lock.acquire()
        try:
            count = reconcile_stale_scan_jobs(db)
            assert count == 1
            db.refresh(old)
            db.refresh(current)
            assert old.status == SCAN_INTERRUPTED
            assert current.status == SCAN_RUNNING
        finally:
            _lock.release()

        db.delete(db.get(ScanJob, old_id))
        db.delete(db.get(ScanJob, current_id))
        db.commit()
