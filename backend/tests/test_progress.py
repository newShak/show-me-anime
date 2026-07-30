"""阅读进度 API 测试。"""

from PIL import Image


def _make_jpeg(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 80), (0, 128, 255)).save(path, format="JPEG")


def test_progress_save_and_load(client, gallery):
    album = gallery / "comic"
    album.mkdir()
    _make_jpeg(album / "1.jpg")
    _make_jpeg(album / "2.jpg")

    client.post("/api/scan/trigger")
    node_id = client.get("/api/nodes").json()[0]["id"]

    empty = client.get(f"/api/nodes/{node_id}/progress")
    assert empty.status_code == 200
    assert empty.json()["page_index"] == 0

    saved = client.put(f"/api/nodes/{node_id}/progress", json={"page_index": 1})
    assert saved.status_code == 200
    assert saved.json()["page_index"] == 1

    loaded = client.get(f"/api/nodes/{node_id}/progress")
    assert loaded.json()["page_index"] == 1


def test_progress_out_of_range(client, gallery):
    album = gallery / "one-page"
    album.mkdir()
    _make_jpeg(album / "1.jpg")
    client.post("/api/scan/trigger")
    node_id = client.get("/api/nodes").json()[0]["id"]

    res = client.put(f"/api/nodes/{node_id}/progress", json={"page_index": 5})
    assert res.status_code == 400


def test_batch_progress(client, gallery):
    album = gallery / "batch-comic"
    album.mkdir()
    _make_jpeg(album / "1.jpg")
    _make_jpeg(album / "2.jpg")
    _make_jpeg(album / "3.jpg")

    client.post("/api/scan/trigger")
    node_id = client.get("/api/nodes").json()[0]["id"]
    client.put(f"/api/nodes/{node_id}/progress", json={"page_index": 1})

    res = client.get("/api/nodes/progress", params={"ids": str(node_id)})
    assert res.status_code == 200
    assert res.json()[0]["page_index"] == 1
