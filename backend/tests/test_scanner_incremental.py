"""增量扫描测试。"""

from pathlib import Path


def _touch(dir_path: Path, name: str) -> None:
    (dir_path / name).write_bytes(b"x")


def test_rescan_unchanged_gallery(client, gallery):
    album = gallery / "cached-album"
    album.mkdir()
    _touch(album, "1.jpg")

    first = client.post("/api/scan/trigger")
    assert first.status_code == 200
    assert first.json()["added"] >= 1

    second = client.post("/api/scan/trigger")
    assert second.status_code == 200
    body = second.json()
    assert body["added"] == 0
    assert body["updated"] == 0
    assert body["removed"] == 0
    assert "skipped_deep" in body["message"]


def test_full_rescan_does_not_skip_deep(client, gallery):
    album = gallery / "full-scan-album"
    album.mkdir()
    _touch(album, "1.jpg")

    client.post("/api/scan/trigger", json={"mode": "incremental"})
    second = client.post("/api/scan/trigger", json={"mode": "full"})
    assert second.status_code == 200
    body = second.json()
    assert body["added"] == 0
    assert body["updated"] == 0
    assert body["removed"] == 0
    assert "mode=full" in body["message"]
    assert "skipped_deep" not in body["message"]


def test_rescan_detects_new_file_in_existing_album(client, gallery):
    album = gallery / "growing-album"
    album.mkdir()
    _touch(album, "1.jpg")
    client.post("/api/scan/trigger")

    _touch(album, "2.jpg")
    res = client.post("/api/scan/trigger")
    assert res.status_code == 200
    body = res.json()
    assert body["added"] == 0
    assert body["updated"] >= 1
    assert body["removed"] == 0

    nodes = client.get("/api/nodes").json()
    node = next(n for n in nodes if n["name"] == "growing-album")
    assert node["image_count"] == 2


def test_hot_path_rescan_does_not_churn_container_cover(client, gallery):
    """watchdog 热路径重扫不应反复清空/恢复容器继承封面。"""
    from PIL import Image

    from app.services.scan_runner import run_scan

    album = gallery / "collection" / "album-a"
    album.mkdir(parents=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(album / "1.jpg", format="JPEG")

    client.post("/api/scan/trigger")
    hint = str((gallery / "collection" / "album-a" / "1.jpg").resolve())
    job = run_scan(source="watchdog", changed_paths=[hint])
    assert job is not None
    assert job.updated == 0


def test_scan_removes_stale_subtree_with_relations(client, gallery):
    """磁盘删除父目录后重扫，应清理子节点及标签/进度关联。"""
    import shutil
    from PIL import Image

    parent = gallery / "gone-parent"
    child = parent / "gone-child"
    child.mkdir(parents=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(child / "1.jpg", format="JPEG")

    client.post("/api/scan/trigger")
    child_node = next(n for n in client.get("/api/nodes").json() if n["name"] == "gone-parent")
    children = client.get("/api/nodes", params={"parent_id": child_node["id"]}).json()
    leaf = children[0]

    tag = client.post("/api/tags", json={"name": "stale-tag"}).json()
    client.put(f"/api/tags/nodes/{leaf['id']}", json={"tag_ids": [tag["id"]]})
    client.put(f"/api/nodes/{leaf['id']}/progress", json={"page_index": 0})

    shutil.rmtree(parent)
    res = client.post("/api/scan/trigger")
    assert res.status_code == 200
    assert res.json()["removed"] >= 2

    names = {n["name"] for n in client.get("/api/nodes").json()}
    assert "gone-parent" not in names
    assert "gone-child" not in names
