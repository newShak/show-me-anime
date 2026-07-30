"""任务记录 API 测试。"""

import time
from pathlib import Path

from PIL import Image

from app.constants import SCAN_DONE, SCAN_RUNNING
from app.db.models import ScanJob, TaskLog
from app.db.session import SessionLocal, get_engine
from app.services.task_log import TASK_REBUILD_THUMBS


def _make_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path, format="JPEG")


def test_task_records_include_scan_mode(client, gallery):
    _make_jpeg(gallery / "album" / "1.jpg")
    client.post("/api/scan/trigger", json={"mode": "full"})

    res = client.get("/api/tasks", params={"page": 1, "pageSize": 10})
    assert res.status_code == 200
    scan = next(item for item in res.json()["items"] if item["task_type"] == "scan")
    assert scan["mode"] == "full"
    assert scan["source"] == "api"


def test_purge_task_records_by_time_range(client):
    now = time.time()
    with SessionLocal(bind=get_engine()) as db:
        db.add(ScanJob(status=SCAN_DONE, source="api", mode="incremental", started_at=now - 86400 * 10))
        db.add(ScanJob(status=SCAN_DONE, source="api", mode="incremental", started_at=now - 3600))
        db.add(ScanJob(status=SCAN_RUNNING, source="api", mode="incremental", started_at=now - 1800))
        db.add(TaskLog(task_type=TASK_REBUILD_THUMBS, status=SCAN_DONE, started_at=now - 86400 * 10))
        db.add(TaskLog(task_type=TASK_REBUILD_THUMBS, status=SCAN_DONE, started_at=now - 7200))
        db.commit()

    res = client.post(
        "/api/tasks/purge",
        json={"startTime": now - 86400 * 2, "endTime": now},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["deletedScans"] == 1
    assert body["deletedLogs"] == 1
    assert body["deleted"] == 2

    list_res = client.get("/api/tasks", params={"page": 1, "pageSize": 20})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 3


def test_purge_task_records_rejects_invalid_range(client):
    res = client.post("/api/tasks/purge", json={"startTime": 200, "endTime": 100})
    assert res.status_code == 400

