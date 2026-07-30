"""纯容器目录封面继承测试。"""

from pathlib import Path

from PIL import Image


def _make_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path, format="JPEG")


def test_container_inherits_child_album_cover(client, gallery):
    album = gallery / "collection" / "series-a"
    _make_jpeg(album / "1.jpg")

    res = client.post("/api/scan/trigger")
    assert res.status_code == 200

    nodes = client.get("/api/nodes").json()
    container = next(n for n in nodes if n["name"] == "collection")
    assert container["node_type"] == "container"
    assert container["cover_rel_path"] == "series-a/1.jpg"

    cover = client.get(f"/api/nodes/{container['id']}/cover/thumb")
    assert cover.status_code == 200


def test_nested_container_inherits_descendant_cover(client, gallery):
    _make_jpeg(gallery / "outer" / "inner" / "album" / "cover.jpg")

    client.post("/api/scan/trigger")
    outer_node = client.get("/api/nodes").json()[0]
    inner_node = client.get("/api/nodes", params={"parent_id": outer_node["id"]}).json()[0]

    assert inner_node["name"] == "inner"
    assert inner_node["cover_rel_path"] == "album/cover.jpg"
    assert outer_node["cover_rel_path"] == "inner/album/cover.jpg"

    cover = client.get(f"/api/nodes/{outer_node['id']}/cover/thumb")
    assert cover.status_code == 200
