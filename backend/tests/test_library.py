"""最近浏览与收藏 API 测试。"""

from PIL import Image


def _make_album(gallery, name: str):
    path = gallery / name
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path / "1.jpg", format="JPEG")


def _album_ids(client):
    return [n["id"] for n in client.get("/api/nodes").json() if n["node_type"] != "container"]


def test_recent_views_touch_trim_and_clear(client, gallery, monkeypatch, tmp_path):
    settings_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.SETTINGS_JSON", settings_json)
    client.put("/api/settings", json={"recent_view_limit": 2})

    _make_album(gallery, "a")
    _make_album(gallery, "b")
    _make_album(gallery, "c")
    client.post("/api/scan/trigger")
    ids = _album_ids(client)
    assert len(ids) == 3

    for nid in ids:
        assert client.post(f"/api/library/recent/{nid}").status_code == 204

    recent = client.get("/api/library/recent").json()
    assert len(recent) == 2
    assert {n["id"] for n in recent} == set(ids[-2:])

    assert client.delete("/api/library/recent").status_code == 204
    assert client.get("/api/library/recent").json() == []


def test_favorites_toggle_list_and_clear(client, gallery):
    _make_album(gallery, "fav-a")
    _make_album(gallery, "fav-b")
    client.post("/api/scan/trigger")
    a_id, b_id = _album_ids(client)

    res = client.post(f"/api/library/favorites/{a_id}")
    assert res.status_code == 200
    assert res.json() == {"node_id": a_id, "favorited": True}

    res = client.post(f"/api/library/favorites/{a_id}")
    assert res.json() == {"node_id": a_id, "favorited": False}

    client.post(f"/api/library/favorites/{a_id}")
    client.post(f"/api/library/favorites/{b_id}")
    assert client.get("/api/library/favorites/ids").json() == [b_id, a_id]

    favs = client.get("/api/library/favorites").json()
    assert favs["total"] == 2
    assert [n["id"] for n in favs["items"]] == [b_id, a_id]

    page = client.get("/api/library/favorites", params={"offset": 1, "limit": 1}).json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["id"] == a_id

    assert client.delete("/api/library/favorites").status_code == 204
    assert client.get("/api/library/favorites/ids").json() == []


def test_library_404_for_missing_node(client):
    assert client.post("/api/library/recent/99999").status_code == 404
    assert client.post("/api/library/favorites/99999").status_code == 404
