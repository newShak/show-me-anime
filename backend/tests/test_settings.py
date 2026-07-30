"""设置 API 测试。"""

from app.config import reload_settings


def test_save_settings_thumb_size(client, tmp_path, monkeypatch):
    settings_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.SETTINGS_JSON", settings_json)

    res = client.put("/api/settings", json={"thumb_max_size": 512})
    assert res.status_code == 200
    body = res.json()
    assert body["thumb_max_size"] == 512
    assert settings_json.exists()

    reload_settings()
    get_res = client.get("/api/settings")
    assert get_res.json()["thumb_max_size"] == 512


def test_save_settings_log_level(client, tmp_path, monkeypatch):
    settings_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.SETTINGS_JSON", settings_json)

    res = client.put("/api/settings", json={"log_level": "DEBUG"})
    assert res.status_code == 200
    assert res.json()["log_level"] == "DEBUG"

    reload_settings()
    assert client.get("/api/settings").json()["log_level"] == "DEBUG"


def test_save_settings_invalid_path(client, tmp_path, monkeypatch):
    settings_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.SETTINGS_JSON", settings_json)

    bad = tmp_path / "not-a-dir"
    bad.write_text("x", encoding="utf-8")
    res = client.put("/api/settings", json={"thumb_dir": str(bad)})
    assert res.status_code == 400


def test_rebuild_thumbs(client, tmp_path, monkeypatch):
    from app.config import get_settings

    thumb_dir = get_settings().thumb_dir
    (thumb_dir / "a.webp").write_bytes(b"x")
    (thumb_dir / "b.webp").write_bytes(b"x")

    res = client.post("/api/settings/rebuild-thumbs")
    assert res.status_code == 200
    body = res.json()
    assert body["deleted"] == 2
    assert not list(thumb_dir.glob("*.webp"))
