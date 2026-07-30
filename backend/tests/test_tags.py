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
