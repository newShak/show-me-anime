"""节点列表排序 API 测试。"""

import os
import time
from pathlib import Path


def _touch(dir_path: Path, name: str) -> None:
    (dir_path / name).write_bytes(b"x")


def _scan(client):
    res = client.post("/api/scan/trigger")
    assert res.status_code == 200
    return res.json()


def test_sort_by_name_natural(client, gallery):
    for name in ("album10", "album2", "album1"):
        folder = gallery / name
        folder.mkdir()
        _touch(folder, "1.jpg")

    _scan(client)

    asc = client.get("/api/nodes", params={"sort_by": "name", "sort_order": "asc"}).json()
    assert [n["name"] for n in asc] == ["album1", "album2", "album10"]

    desc = client.get("/api/nodes", params={"sort_by": "name", "sort_order": "desc"}).json()
    assert [n["name"] for n in desc] == ["album10", "album2", "album1"]


def test_sort_by_mtime(client, gallery):
    a = gallery / "older"
    b = gallery / "newer"
    a.mkdir()
    time.sleep(0.05)
    b.mkdir()
    _touch(a, "1.jpg")
    _touch(b, "1.jpg")
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    _scan(client)

    asc = client.get("/api/nodes", params={"sort_by": "mtime", "sort_order": "asc"}).json()
    assert [n["name"] for n in asc] == ["older", "newer"]

    desc = client.get("/api/nodes", params={"sort_by": "mtime", "sort_order": "desc"}).json()
    assert [n["name"] for n in desc] == ["newer", "older"]


def test_sort_invalid_params(client):
    res = client.get("/api/nodes", params={"sort_by": "invalid"})
    assert res.status_code == 400
