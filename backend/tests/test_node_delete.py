"""节点批量删除测试。"""

from PIL import Image


def _make_album(gallery, rel: str, files: list[str] | None = None):
    path = gallery / rel
    path.mkdir(parents=True, exist_ok=True)
    for name in files or ["1.jpg"]:
        Image.new("RGB", (40, 40), (255, 0, 0)).save(path / name, format="JPEG")


def test_batch_delete_nodes(client, gallery):
    _make_album(gallery, "del-a", ["1.jpg"])
    _make_album(gallery, "del-b", ["1.jpg"])
    _make_album(gallery, "keep-me", ["1.jpg"])
    client.post("/api/scan/trigger")

    nodes = client.get("/api/nodes").json()
    ids = [n["id"] for n in nodes if n["name"] in {"del-a", "del-b"}]

    res = client.post("/api/nodes/batch-delete", json={"ids": ids})
    assert res.status_code == 200
    assert res.json()["deleted"] >= 2

    remaining = client.get("/api/nodes").json()
    names = {n["name"] for n in remaining}
    assert "del-a" not in names
    assert "del-b" not in names
    assert "keep-me" in names
    assert not (gallery / "del-a").exists()
    assert (gallery / "keep-me").exists()


def test_batch_delete_dedupe_parent_child(client, gallery):
    _make_album(gallery, "parent/child", ["1.jpg"])
    client.post("/api/scan/trigger")

    all_nodes = client.get("/api/nodes").json()
    parent = next(n for n in all_nodes if n["name"] == "parent")
    children = client.get("/api/nodes", params={"parent_id": parent["id"]}).json()
    child_id = children[0]["id"]

    res = client.post("/api/nodes/batch-delete", json={"ids": [parent["id"], child_id]})
    assert res.status_code == 200
    assert not (gallery / "parent").exists()
