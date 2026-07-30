"""集合搜索 API 测试。"""

from PIL import Image


def _make_album(gallery, name: str, image_name: str = "1.jpg"):
    path = gallery / name
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path / image_name, format="JPEG")


def test_search_by_folder_name(client, gallery):
    _make_album(gallery, "my-comic-collection")
    _make_album(gallery, "other-folder")
    client.post("/api/scan/trigger")

    res = client.get("/api/search", params={"q": "comic"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any("comic" in item["name"].lower() or "comic" in item["path"].lower() for item in body["items"])


def test_search_does_not_find_image_filename(client, gallery):
    _make_album(gallery, "album-a", "secret-page-99.jpg")
    client.post("/api/scan/trigger")

    res = client.get("/api/search", params={"q": "secret-page-99"})
    assert res.status_code == 200
    assert res.json()["total"] == 0
