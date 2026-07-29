"""扫描与相册 API 测试。"""

from pathlib import Path


def _touch(dir_path: Path, name: str) -> None:
    (dir_path / name).write_bytes(b"x")


def test_scan_and_list_images(client, gallery):
    album = gallery / "comic-a"
    album.mkdir()
    _touch(album, "10.jpg")
    _touch(album, "2.jpg")
    _touch(album, "1.jpg")

    scan_res = client.post("/api/scan/trigger")
    assert scan_res.status_code == 200
    assert scan_res.json()["added"] >= 1

    nodes_res = client.get("/api/nodes")
    assert nodes_res.status_code == 200
    nodes = nodes_res.json()
    assert len(nodes) == 1
    assert nodes[0]["name"] == "comic-a"
    assert nodes[0]["node_type"] == "album"

    images_res = client.get(f"/api/nodes/{nodes[0]['id']}/images")
    assert images_res.status_code == 200
    body = images_res.json()
    assert body["total"] == 3
    assert [item["filename"] for item in body["items"]] == ["1.jpg", "2.jpg", "10.jpg"]


def test_nested_nodes(client, gallery):
    root = gallery / "comics" / "series-a"
    root.mkdir(parents=True)
    _touch(root, "001.jpg")

    client.post("/api/scan/trigger")
    top = client.get("/api/nodes").json()
    assert len(top) == 1
    assert top[0]["name"] == "comics"

    children = client.get("/api/nodes", params={"parent_id": top[0]["id"]}).json()
    assert len(children) == 1
    assert children[0]["name"] == "series-a"
