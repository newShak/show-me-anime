"""图片文件与缩略图 API 测试。"""

from io import BytesIO

from PIL import Image


def _make_jpeg(path, color=(255, 0, 0)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 160), color).save(path, format="JPEG")


def test_image_file_and_thumb(client, gallery):
    album = gallery / "sample"
    album.mkdir()
    _make_jpeg(album / "1.jpg")

    scan = client.post("/api/scan/trigger")
    node_id = client.get("/api/nodes").json()[0]["id"]

    file_res = client.get(f"/api/nodes/{node_id}/images/0/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"].startswith("image/")

    thumb_res = client.get(f"/api/nodes/{node_id}/images/0/thumb")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/webp"

    cover_res = client.get(f"/api/nodes/{node_id}/cover/thumb")
    assert cover_res.status_code == 200

    assert scan.status_code == 200
