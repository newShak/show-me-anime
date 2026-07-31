"""最近添加与批量查询测试。"""

from PIL import Image


def _make_album(gallery, name: str):
    path = gallery / name
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 40), (255, 0, 0)).save(path / "1.jpg", format="JPEG")


def test_recent_and_batch_nodes(client, gallery):
    _make_album(gallery, "older")
    _make_album(gallery, "newer")
    client.post("/api/scan/trigger")

    recent = client.get("/api/nodes/recent", params={"limit": 1}).json()
    assert len(recent) == 1

    ids = [n["id"] for n in client.get("/api/nodes").json()]
    batch = client.get("/api/nodes/batch", params={"ids": ",".join(map(str, reversed(ids)))}).json()
    assert len(batch) == len(ids)
    assert [n["id"] for n in batch] == list(reversed(ids))
