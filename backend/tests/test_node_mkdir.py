"""mkdir 节点目录测试。"""


def test_mkdir_root(client, gallery):
    res = client.post("/api/nodes/mkdir", json={"name": "download-test"})
    assert res.status_code == 200
    body = res.json()
    assert body["path"] == "download-test"
    assert (gallery / "download-test").is_dir()

    dup = client.post("/api/nodes/mkdir", json={"name": "download-test"})
    assert dup.status_code == 200
    assert dup.json()["id"] == body["id"]


def test_mkdir_nested(client, gallery):
    root = client.post("/api/nodes/mkdir", json={"name": "imports-batch"}).json()
    child = client.post("/api/nodes/mkdir", json={"parent_id": root["id"], "name": "wnacg"})
    assert child.status_code == 200
    assert child.json()["path"] == "imports-batch/wnacg"
    assert (gallery / "imports-batch" / "wnacg").is_dir()
