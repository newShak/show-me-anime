"""标签 API 测试。"""

from PIL import Image


def _make_album(gallery, name: str):
    path = gallery / name
    path.mkdir(parents=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path / "1.jpg", format="JPEG")


def test_tag_crud_and_search(client, gallery):
    _make_album(gallery, "tagged-album")
    client.post("/api/scan/trigger")

    create = client.post("/api/tags", json={"name": "科幻"})
    assert create.status_code == 200
    tag_id = create.json()["id"]

    nodes = client.get("/api/nodes").json()
    node_id = next(n["id"] for n in nodes if n["name"] == "tagged-album")

    assign = client.put(f"/api/tags/nodes/{node_id}", json={"tag_ids": [tag_id]})
    assert assign.status_code == 200
    assert assign.json()[0]["name"] == "科幻"

    search = client.get("/api/search", params={"q": "科幻"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    listed = client.get(f"/api/tags/nodes/{node_id}")
    assert listed.json()[0]["id"] == tag_id

    delete = client.delete(f"/api/tags/{tag_id}")
    assert delete.status_code == 200
    assert client.get("/api/tags").json() == []


def test_create_duplicate_tag(client):
    client.post("/api/tags", json={"name": "dup"})
    res = client.post("/api/tags", json={"name": "dup"})
    assert res.status_code == 409


def test_batch_add_and_remove_node_tag(client, gallery):
    _make_album(gallery, "album-a")
    _make_album(gallery, "album-b")
    client.post("/api/scan/trigger")

    t1 = client.post("/api/tags", json={"name": "动作"}).json()["id"]
    t2 = client.post("/api/tags", json={"name": "冒险"}).json()["id"]
    nodes = client.get("/api/nodes").json()
    ids = [n["id"] for n in nodes]

    batch = client.post("/api/tags/nodes/batch-add", json={"node_ids": ids, "tag_ids": [t1]})
    assert batch.status_code == 200
    assert batch.json()["updated"] == 2

    listed = client.get("/api/tags/nodes/tags", params={"ids": ",".join(map(str, ids))})
    assert all(t1 in [t["id"] for t in item["tags"]] for item in listed.json())

    remove = client.delete(f"/api/tags/nodes/{ids[0]}/tags/{t1}")
    assert remove.status_code == 200

    batch2 = client.post(
        "/api/tags/nodes/batch-add",
        json={"node_ids": ids, "tag_ids": [t2]},
    )
    assert batch2.json()["updated"] == 2
