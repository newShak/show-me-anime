"""任务记录 API 测试。"""

from pathlib import Path

from PIL import Image


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
