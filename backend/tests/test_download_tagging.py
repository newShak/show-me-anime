"""下载完成后打标测试。"""

import time


def test_download_job_applies_tags(client, gallery):
    local = client.post("/api/tags", json={"name": "本地标记"}).json()["id"]

    search = client.get("/api/download/search", params={"q": "tag-job"}).json()
    item = search["items"][0]

    create = client.post(
        "/api/download/jobs",
        json={
            "source": "wnacg",
            "album_id": item["id"],
            "title": item["title"],
            "target_rel_path": "mock-import/tagged-album",
            "tag_ids": [local],
            "import_remote_tags": ["远程A", "远程B"],
        },
    )
    assert create.status_code == 200
    job_id = create.json()["id"]

    job = create.json()
    for _ in range(50):
        job = client.get(f"/api/download/jobs/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)
    assert job["status"] == "done"

    nodes = client.get("/api/nodes").json()
    parent = next(n for n in nodes if n["name"] == "mock-import")
    children = client.get("/api/nodes", params={"parent_id": parent["id"]}).json()
    node = next(n for n in children if n["name"] == "tagged-album")
    tags = client.get(f"/api/tags/nodes/{node['id']}").json()
    names = {t["name"] for t in tags}
    assert "本地标记" in names
    assert "远程A" in names
    assert "远程B" in names


def test_ensure_tags(client):
    first = client.post("/api/tags/ensure", json={"names": ["导入1", "导入2"]})
    assert first.status_code == 200
    tags = first.json()["tags"]
    assert len(tags) == 2

    second = client.post("/api/tags/ensure", json={"names": ["导入1", "导入3"]})
    assert second.status_code == 200
    merged = second.json()["tags"]
    assert len(merged) == 2
    assert merged[0]["name"] == "导入1"
    assert merged[1]["name"] == "导入3"
