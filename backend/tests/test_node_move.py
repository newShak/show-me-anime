"""节点移动测试。"""

from PIL import Image


def _make_album(gallery, rel: str, files: list[str] | None = None):
    path = gallery / rel
    path.mkdir(parents=True, exist_ok=True)
    for name in files or ["1.jpg"]:
        Image.new("RGB", (40, 40), (255, 0, 0)).save(path / name, format="JPEG")


def _scan(client):
    client.post("/api/scan/trigger")


def _find_node(nodes, name):
    return next(n for n in nodes if n["name"] == name)


def test_move_album_to_folder(client, gallery):
    _make_album(gallery, "src-album", ["1.jpg"])
    _make_album(gallery, "dest-dir/placeholder", ["1.jpg"])
    _scan(client)

    root = client.get("/api/nodes").json()
    album = _find_node(root, "src-album")
    dest_children = client.get("/api/nodes", params={"parent_id": _find_node(root, "dest-dir")["id"]}).json()
    dest_dir = _find_node(root, "dest-dir")

    res = client.post("/api/nodes/move", json={"ids": [album["id"]], "target_parent_id": dest_dir["id"]})
    assert res.status_code == 200
    body = res.json()
    assert body["moved"] == 1
    assert not body["errors"]

    assert not (gallery / "src-album").exists()
    assert (gallery / "dest-dir" / "src-album" / "1.jpg").exists()

    moved = client.get(f"/api/nodes/{album['id']}").json()
    assert moved["path"] == "dest-dir/src-album"
    assert moved["parent_id"] == dest_dir["id"]

    dest_children_after = client.get("/api/nodes", params={"parent_id": dest_dir["id"]}).json()
    names = {n["name"] for n in dest_children_after}
    assert "src-album" in names
    assert len(dest_children) + 1 == len(dest_children_after)


def test_move_album_to_root(client, gallery):
    _make_album(gallery, "wrap/moved-out", ["1.jpg"])
    _scan(client)

    wrap_children = client.get("/api/nodes").json()
    wrap = _find_node(wrap_children, "wrap")
    album = client.get("/api/nodes", params={"parent_id": wrap["id"]}).json()[0]

    res = client.post("/api/nodes/move", json={"ids": [album["id"]], "target_parent_id": None})
    assert res.status_code == 200
    assert res.json()["moved"] == 1

    assert (gallery / "moved-out" / "1.jpg").exists()
    assert not (gallery / "wrap" / "moved-out").exists()

    moved = client.get(f"/api/nodes/{album['id']}").json()
    assert moved["path"] == "moved-out"
    assert moved["parent_id"] is None


def test_move_rejects_into_self(client, gallery):
    _make_album(gallery, "parent/child", ["1.jpg"])
    _scan(client)

    root = client.get("/api/nodes").json()
    parent = _find_node(root, "parent")
    child = client.get("/api/nodes", params={"parent_id": parent["id"]}).json()[0]

    res = client.post("/api/nodes/move", json={"ids": [parent["id"]], "target_parent_id": child["id"]})
    assert res.status_code == 200
    assert res.json()["moved"] == 0
    assert res.json()["errors"]


def test_move_album_into_album(client, gallery):
    _make_album(gallery, "target-album", ["1.jpg"])
    _make_album(gallery, "moving-album", ["1.jpg"])
    _scan(client)

    root = client.get("/api/nodes").json()
    target = _find_node(root, "target-album")
    moving = _find_node(root, "moving-album")

    res = client.post("/api/nodes/move", json={"ids": [moving["id"]], "target_parent_id": target["id"]})
    assert res.status_code == 200
    assert res.json()["moved"] == 1
    assert (gallery / "target-album" / "moving-album" / "1.jpg").exists()

    moved = client.get(f"/api/nodes/{moving['id']}").json()
    assert moved["path"] == "target-album/moving-album"
    assert moved["parent_id"] == target["id"]


def test_move_batch_dedupe_parent_child(client, gallery):
    _make_album(gallery, "batch-parent/batch-child", ["1.jpg"])
    _scan(client)

    root = client.get("/api/nodes").json()
    parent = _find_node(root, "batch-parent")
    child = client.get("/api/nodes", params={"parent_id": parent["id"]}).json()[0]
    _make_album(gallery, "target-dir/x", ["1.jpg"])
    _scan(client)
    target = _find_node(client.get("/api/nodes").json(), "target-dir")

    res = client.post(
        "/api/nodes/move",
        json={"ids": [parent["id"], child["id"]], "target_parent_id": target["id"]},
    )
    assert res.status_code == 200
    assert res.json()["moved"] == 1
    assert (gallery / "target-dir" / "batch-parent" / "batch-child" / "1.jpg").exists()
