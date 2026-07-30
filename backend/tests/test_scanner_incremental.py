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
