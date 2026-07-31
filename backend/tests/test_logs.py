"""日志 API 测试。"""


def test_log_files_and_content(client, tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "app.log"
    log_file.write_text("line-1\nline-2\nline-3\n", encoding="utf-8")

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("LOG_FILE_ENABLED", "true")
    from app.config import reload_settings

    reload_settings()

    files = client.get("/api/logs/files")
    assert files.status_code == 200
    body = files.json()
    assert body["enabled"] is True
    assert any(item["name"] == "app.log" for item in body["items"])

    content = client.get("/api/logs/content", params={"file": "app.log", "tailLines": 2, "offset": 0})
    assert content.status_code == 200
    payload = content.json()
    assert "line-2" in payload["content"]
    assert "line-3" in payload["content"]
    assert payload["offset"] > 0

    append = client.get(
        "/api/logs/content",
        params={"file": "app.log", "tailLines": 2, "offset": payload["offset"]},
    )
    assert append.status_code == 200
    assert append.json()["append"] is True

    bad = client.get("/api/logs/content", params={"file": "../secret.log"})
    assert bad.status_code == 400


def test_log_content_disabled(client, monkeypatch):
    monkeypatch.setenv("LOG_FILE_ENABLED", "false")
    from app.config import reload_settings

    reload_settings()
    res = client.get("/api/logs/content")
    assert res.status_code == 400
