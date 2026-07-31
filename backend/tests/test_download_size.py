"""下载记录大小统计测试。"""

from app.services.download.size import cache_dir_size, dest_dir_size


def test_dest_dir_size(tmp_path):
    dest = tmp_path / "album"
    dest.mkdir()
    (dest / "001.jpg").write_bytes(b"x" * 100)
    (dest / "002.jpg").write_bytes(b"y" * 50)
    (dest / ".hidden").write_bytes(b"z" * 999)
    assert dest_dir_size(dest) == 150


def test_cache_dir_size_includes_zip(tmp_path):
    cache = tmp_path / "job-1"
    cache.mkdir()
    (cache / "_download.zip").write_bytes(b"z" * 1024)
    (cache / "001.jpg").write_bytes(b"x" * 10)
    assert cache_dir_size(cache) == 1034


def test_download_records_size_bytes(client, gallery):
    search = client.get("/api/download/search", params={"q": "size"}).json()
    item = search["items"][0]

    create = client.post(
        "/api/download/jobs",
        json={
            "source": "wnacg",
            "album_id": item["id"],
            "title": item["title"],
            "target_rel_path": "mock-import/size-test",
        },
    )
    assert create.status_code == 200
    job_id = create.json()["id"]

    import time

    for _ in range(50):
        job = client.get(f"/api/download/jobs/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)

    assert job["status"] == "done"

    records = client.get("/api/download/records", params={"page": 1, "pageSize": 10}).json()
    row = next(r for r in records["items"] if r["id"] == job_id)
    assert row["size_bytes"] > 0
    assert records["page_total_bytes"] >= row["size_bytes"]

    dest = gallery / "mock-import" / "size-test"
    assert row["size_bytes"] == dest_dir_size(dest)


def test_download_records_skip_existing_size(client, gallery):
    existing = gallery / "mock-import" / "size-skip"
    existing.mkdir(parents=True)
    (existing / "001.jpg").write_bytes(b"a" * 200)

    res = client.post(
        "/api/download/jobs",
        json={
            "source": "wnacg",
            "album_id": "album-size-skip",
            "title": "跳过统计",
            "target_rel_path": "mock-import/size-skip",
        },
    )
    job_id = res.json()["id"]

    import time

    for _ in range(50):
        job = client.get(f"/api/download/jobs/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)

    records = client.get("/api/download/records", params={"page": 1, "pageSize": 10}).json()
    row = next(r for r in records["items"] if r["id"] == job_id)
    assert row["size_bytes"] == 200
