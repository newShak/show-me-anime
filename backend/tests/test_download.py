"""外站下载 API 测试。"""


def test_download_sources(client):
    res = client.get("/api/download/sources")
    assert res.status_code == 200
    sources = res.json()
    assert any(s["id"] == "wnacg" for s in sources)


def test_download_search_mock(client):
    res = client.get("/api/download/search", params={"q": "test", "page": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] > 0
    assert len(body["items"]) > 0
    assert body["items"][0]["source"] == "wnacg"


def test_download_detail_and_cover(client):
    search = client.get("/api/download/search", params={"q": "x"}).json()
    album_id = search["items"][0]["id"]

    detail = client.get("/api/download/detail", params={"id": album_id})
    assert detail.status_code == 200
    body = detail.json()
    assert body["default_target_rel_path"]
    assert body["default_parent_rel_path"]
    assert len(body["preview_urls"]) >= 1
    assert len(body["preview_urls"]) <= 10
    assert body["preview_has_more"] is True
    assert body["preview_total"] >= len(body["preview_urls"])

    cover = client.get("/api/download/cover", params={"id": album_id})
    assert cover.status_code == 200
    assert cover.headers["content-type"].startswith("image/")

    preview = client.get("/api/download/preview", params={"id": album_id, "n": 0})
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/")

    more = client.get(
        "/api/download/previews",
        params={"id": album_id, "offset": len(body["preview_urls"]), "limit": 10},
    )
    assert more.status_code == 200
    batch = more.json()
    assert batch["count"] >= 1
    assert batch["offset"] == len(body["preview_urls"])


def test_download_job_mock(client, gallery):
    search = client.get("/api/download/search", params={"q": "job"}).json()
    item = search["items"][0]

    create = client.post(
        "/api/download/jobs",
        json={
            "source": "wnacg",
            "album_id": item["id"],
            "title": item["title"],
            "target_rel_path": "mock-import/test-album",
        },
    )
    assert create.status_code == 200
    job_id = create.json()["id"]

    import time

    job = create.json()
    for _ in range(50):
        job = client.get(f"/api/download/jobs/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)

    assert job["status"] == "done"
    assert (gallery / "mock-import" / "test-album" / "001.jpg").is_file()

    from app.config import get_settings

    assert not (get_settings().download_cache_dir / job_id).exists()

    records = client.get("/api/download/records", params={"page": 1, "pageSize": 10})
    assert records.status_code == 200
    body = records.json()
    assert body["total"] >= 1
    assert any(r["id"] == job_id for r in body["items"])


def test_download_browse_mock(client):
    res = client.get("/api/download/browse", params={"page": 1, "pageSize": 24})
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "首頁"
    assert len(body["items"]) > 0
    assert len(body["nav"]) >= 4
    assert body["nav"][0]["label"] == "首頁"

    cate = client.get("/api/download/browse", params={"page": 1, "pageSize": 24, "cateId": 1})
    assert cate.status_code == 200
    cate_body = cate.json()
    assert cate_body["cate_id"] == 1
    assert "漢化" in cate_body["title"]
    assert len(cate_body["items"]) > 0


def test_download_options(client):
    res = client.get("/api/download/options")
    assert res.status_code == 200
    body = res.json()
    assert body["preview_batch_size"] >= 1
    assert body["concurrency"] >= 1


def test_download_job_skips_existing_path(client, gallery):
    existing = gallery / "mock-import" / "exists-album"
    existing.mkdir(parents=True)
    (existing / "001.jpg").write_bytes(b"x")
    (existing / "002.jpg").write_bytes(b"x")
    (existing / "003.jpg").write_bytes(b"x")

    res = client.post(
        "/api/download/jobs",
        json={
            "source": "wnacg",
            "album_id": "album-dup",
            "title": "重复路径",
            "target_rel_path": "mock-import/exists-album",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["target_existed"] is True

    import time

    job = body
    for _ in range(50):
        job = client.get(f"/api/download/jobs/{job['id']}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)

    assert job["status"] == "done"
    assert job["skipped_files"] == 3
    assert job["saved_files"] == 0
    assert "跳过" in (job["message"] or "")


def test_download_jobs_batch(client):
    search = client.get("/api/download/search", params={"q": "batch"}).json()
    picked = search["items"][:2]
    res = client.post(
        "/api/download/jobs/batch",
        json={
            "parent_rel_path": "mock-import/batch",
            "items": [
                {"source": "wnacg", "album_id": i["id"], "title": i["title"]}
                for i in picked
            ],
        },
    )
    assert res.status_code == 200
    jobs = res.json()["jobs"]
    assert len(jobs) == 2
    paths = {j["target_rel_path"] for j in jobs}
    assert len(paths) == 2
    assert all(p.startswith("mock-import/batch/") for p in paths)


def test_clear_download_cache(client):
    from app.config import get_settings

    cache = get_settings().download_cache_dir
    work = cache / "stale-job"
    work.mkdir(parents=True)
    (work / "_download.zip").write_bytes(b"partial")
    res = client.post("/api/download/cache/clear")
    assert res.status_code == 200
    assert res.json()["deleted"] >= 1
    assert not work.exists()


def test_download_record_resumable(client):
    from app.config import get_settings
    from app.db.session import SessionLocal, get_engine
    from app.services.download.records import create_record
    from app.services.download.types import DownloadJobState

    job = DownloadJobState(
        id="resumable1",
        source="wnacg",
        album_id="album-x",
        title="续传测试",
        target_rel_path="imports/resume-test",
        status="failed",
        message="network error",
    )
    db = SessionLocal(bind=get_engine())
    try:
        create_record(db, job)
    finally:
        db.close()

    cache = get_settings().download_cache_dir / "resumable1"
    cache.mkdir(parents=True)
    (cache / "_download.zip").write_bytes(b"PK\x03\x04" + b"x" * 64)

    res = client.get("/api/download/records", params={"page": 1, "pageSize": 20})
    assert res.status_code == 200
    item = next(r for r in res.json()["items"] if r["id"] == "resumable1")
    assert item["resumable"] is True


def test_resume_download_job(client):
    from app.config import get_settings
    from app.db.session import SessionLocal, get_engine
    from app.services.download.records import create_record
    from app.services.download.types import DownloadJobState

    job = DownloadJobState(
        id="resume2",
        source="wnacg",
        album_id="album-y",
        title="续传任务",
        target_rel_path="imports/resume-run",
        status="failed",
    )
    db = SessionLocal(bind=get_engine())
    try:
        create_record(db, job)
    finally:
        db.close()

    cache = get_settings().download_cache_dir / "resume2"
    cache.mkdir(parents=True)
    (cache / "_download.zip").write_bytes(b"partial-data")

    res = client.post("/api/download/jobs/resume2/resume")
    assert res.status_code == 200
    assert res.json()["status"] in {"pending", "running"}


def test_resume_download_job_no_partial(client):
    from app.db.session import SessionLocal, get_engine
    from app.services.download.records import create_record
    from app.services.download.types import DownloadJobState

    job = DownloadJobState(
        id="noresumable",
        source="wnacg",
        album_id="album-z",
        title="无缓存",
        target_rel_path="imports/no-cache",
        status="failed",
    )
    db = SessionLocal(bind=get_engine())
    try:
        create_record(db, job)
    finally:
        db.close()

    res = client.post("/api/download/jobs/noresumable/retry")
    assert res.status_code == 200
    assert res.json()["status"] in {"pending", "running"}
