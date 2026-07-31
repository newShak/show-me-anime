"""最近添加与批量查询测试。"""

import time

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
    assert recent["total"] >= 1
    assert len(recent["items"]) == 1
    assert "created_at" in recent["items"][0]

    ids = [n["id"] for n in client.get("/api/nodes").json()]
    batch = client.get("/api/nodes/batch", params={"ids": ",".join(map(str, reversed(ids)))}).json()
    assert len(batch) == len(ids)
    assert [n["id"] for n in batch] == list(reversed(ids))


def test_recent_nodes_range_and_offset(client, gallery):
    from app.db.models import Node
    from app.db.session import SessionLocal, get_engine

    _make_album(gallery, "a")
    _make_album(gallery, "b")
    client.post("/api/scan/trigger")

    now = time.time()
    db = SessionLocal(bind=get_engine())
    try:
        nodes = db.query(Node).filter(Node.name.in_(["a", "b"])).all()
        for i, node in enumerate(sorted(nodes, key=lambda n: n.name)):
            node.created_at = now - i * 86400
        db.commit()
    finally:
        db.close()

    since = now - 86400 * 2
    res = client.get("/api/nodes/recent", params={"since": since, "until": now, "offset": 0, "limit": 1}).json()
    assert res["total"] == 2
    assert len(res["items"]) == 1

    page2 = client.get(
        "/api/nodes/recent",
        params={"since": since, "until": now, "offset": 1, "limit": 1},
    ).json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] != res["items"][0]["id"]
