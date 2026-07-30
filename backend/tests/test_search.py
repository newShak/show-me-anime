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


def test_search_substring_chinese_and_digits(client, gallery):
    _make_album(gallery, "东京")
    _make_album(gallery, "东京222")
    _make_album(gallery, "素晴")
    client.post("/api/scan/trigger")

    jing = client.get("/api/search", params={"q": "京"}).json()
    assert jing["total"] == 2
    assert {item["name"] for item in jing["items"]} == {"东京", "东京222"}

    digits = client.get("/api/search", params={"q": "222"}).json()
    assert digits["total"] == 1
    assert digits["items"][0]["name"] == "东京222"


def test_search_by_tags_or(client, gallery):
    _make_album(gallery, "album-a")
    _make_album(gallery, "album-b")
    _make_album(gallery, "album-c")
    client.post("/api/scan/trigger")

    t1 = client.post("/api/tags", json={"name": "科幻"}).json()["id"]
    t2 = client.post("/api/tags", json={"name": "冒险"}).json()["id"]
    nodes = {n["name"]: n["id"] for n in client.get("/api/nodes").json()}

    client.put(f"/api/tags/nodes/{nodes['album-a']}", json={"tag_ids": [t1]})
    client.put(f"/api/tags/nodes/{nodes['album-b']}", json={"tag_ids": [t2]})

    res = client.get("/api/search", params={"tags": f"{t1},{t2}"})
    assert res.status_code == 200
    names = {item["name"] for item in res.json()["items"]}
    assert names == {"album-a", "album-b"}

    single = client.get("/api/search", params={"tags": str(t1)}).json()
    assert len(single["items"]) == 1
    assert single["items"][0]["name"] == "album-a"
