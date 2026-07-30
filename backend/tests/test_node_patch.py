"""节点 PATCH API 测试。"""

from PIL import Image


def _make_album(gallery, names: list[str]):
    path = gallery / "patch-album"
    path.mkdir(parents=True)
    for name in names:
        Image.new("RGB", (40, 40), (255, 0, 0)).save(path / name, format="JPEG")


def test_patch_node_type_and_cover(client, gallery):
    _make_album(gallery, ["1.jpg", "2.jpg", "10.jpg"])
    client.post("/api/scan/trigger")

    nodes = client.get("/api/nodes").json()
    node_id = next(n["id"] for n in nodes if n["name"] == "patch-album")

    patch = client.patch(f"/api/nodes/{node_id}", json={"node_type": "album", "cover_index": 2})
    assert patch.status_code == 200
    body = patch.json()
    assert body["node_type"] == "album"
    assert body["cover_rel_path"] == "10.jpg"

    cover = client.get(f"/api/nodes/{node_id}/cover/thumb")
    assert cover.status_code == 200


def test_patch_invalid_node_type(client, gallery):
    _make_album(gallery, ["1.jpg"])
    client.post("/api/scan/trigger")
    node_id = client.get("/api/nodes").json()[0]["id"]

    res = client.patch(f"/api/nodes/{node_id}", json={"node_type": "invalid"})
    assert res.status_code == 400
