"""容器自选封面测试。"""

from pathlib import Path

from PIL import Image


def _make_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path, format="JPEG")


def _scan_container(client, gallery):
    _make_jpeg(gallery / "collection" / "series-a" / "1.jpg")
    _make_jpeg(gallery / "collection" / "series-b" / "2.jpg")
    client.post("/api/scan/trigger")
    nodes = client.get("/api/nodes").json()
    return next(n for n in nodes if n["name"] == "collection")


def test_list_cover_candidates(client, gallery):
    container = _scan_container(client, gallery)
    res = client.get(f"/api/nodes/{container['id']}/cover/candidates")
    assert res.status_code == 200
    values = {item["value"] for item in res.json()["items"]}
    assert values == {"series-a/1.jpg", "series-b/2.jpg"}


def test_manual_cover_persists_after_rescan(client, gallery):
    container = _scan_container(client, gallery)
    assert container["cover_rel_path"] == "series-a/1.jpg"

    patch = client.patch(
        f"/api/nodes/{container['id']}",
        json={"cover_rel_path": "series-b/2.jpg", "cover_manual": True},
    )
    assert patch.status_code == 200
    assert patch.json()["cover_rel_path"] == "series-b/2.jpg"
    assert patch.json()["cover_manual"] is True

    client.post("/api/scan/trigger")
    refreshed = client.get(f"/api/nodes/{container['id']}").json()
    assert refreshed["cover_rel_path"] == "series-b/2.jpg"
    assert refreshed["cover_manual"] is True

    cover = client.get(f"/api/nodes/{container['id']}/cover/thumb")
    assert cover.status_code == 200


def test_reset_cover_to_auto(client, gallery):
    container = _scan_container(client, gallery)
    client.patch(
        f"/api/nodes/{container['id']}",
        json={"cover_rel_path": "series-b/2.jpg", "cover_manual": True},
    )

    patch = client.patch(f"/api/nodes/{container['id']}", json={"cover_manual": False})
    assert patch.status_code == 200
    body = patch.json()
    assert body["cover_manual"] is False
    assert body["cover_rel_path"] == "series-a/1.jpg"
