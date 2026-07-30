"""压缩包扫描与阅读测试。"""

import zipfile
from io import BytesIO

from PIL import Image


def _jpeg_bytes(color=(255, 0, 0)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (80, 120), color).save(buf, format="JPEG")
    return buf.getvalue()


def _make_zip(path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def test_scan_zip_album(client, gallery):
    archive = gallery / "comic.cbz"
    _make_zip(archive, {"10.jpg": _jpeg_bytes(), "2.jpg": _jpeg_bytes(), "1.jpg": _jpeg_bytes()})

    res = client.post("/api/scan/trigger")
    assert res.status_code == 200

    nodes = client.get("/api/nodes").json()
    assert len(nodes) == 1
    assert nodes[0]["name"] == "comic"
    assert nodes[0]["source_type"] == "zip"
    assert nodes[0]["node_type"] == "album"
    assert nodes[0]["image_count"] == 3

    node_id = nodes[0]["id"]
    images = client.get(f"/api/nodes/{node_id}/images").json()
    assert [item["filename"] for item in images["items"]] == ["1.jpg", "2.jpg", "10.jpg"]

    file_res = client.get(f"/api/nodes/{node_id}/images/0/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"].startswith("image/")

    thumb_res = client.get(f"/api/nodes/{node_id}/images/1/thumb")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/webp"

    from app.config import get_settings

    extract_dir = get_settings().thumb_dir.parent / "extract_cache"
    assert not extract_dir.exists() or not any(extract_dir.iterdir())


def test_zip_in_folder(client, gallery):
    folder = gallery / "packs"
    folder.mkdir()
    _make_zip(folder / "a.zip", {"001.png": _jpeg_bytes()})
    _make_zip(folder / "b.zip", {"002.png": _jpeg_bytes()})

    client.post("/api/scan/trigger")
    top = client.get("/api/nodes").json()
    assert len(top) == 1
    assert top[0]["name"] == "packs"
    assert top[0]["node_type"] == "container"

    children = client.get("/api/nodes", params={"parent_id": top[0]["id"]}).json()
    assert len(children) == 2
    assert {n["name"] for n in children} == {"a", "b"}
    assert all(n["source_type"] == "zip" for n in children)


def test_delete_zip_album(client, gallery):
    archive = gallery / "remove.cbz"
    _make_zip(archive, {"1.jpg": _jpeg_bytes()})
    client.post("/api/scan/trigger")

    node = next(n for n in client.get("/api/nodes").json() if n["source_type"] == "zip")
    res = client.post("/api/nodes/batch-delete", json={"ids": [node["id"]]})
    assert res.status_code == 200
    assert res.json()["deleted"] == 1
    assert not archive.exists()
    assert client.get("/api/nodes").json() == []
