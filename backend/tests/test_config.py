"""配置加载测试。"""

from app.config import PROJECT_ROOT, get_settings, reload_settings


def test_default_paths(client, monkeypatch):
    monkeypatch.delenv("GALLERY_ROOT", raising=False)
    monkeypatch.delenv("THUMB_DIR", raising=False)
    reload_settings()
    settings = get_settings()
    assert settings.gallery_root == (PROJECT_ROOT / "gallery").resolve()
    assert settings.thumb_dir == (PROJECT_ROOT / "data" / "thumbs").resolve()


def test_custom_paths(client, monkeypatch, tmp_path):
    gallery = tmp_path / "custom-gallery"
    thumbs = tmp_path / "custom-thumbs"
    gallery.mkdir()
    thumbs.mkdir()
    monkeypatch.setenv("GALLERY_ROOT", str(gallery))
    monkeypatch.setenv("THUMB_DIR", str(thumbs))
    reload_settings()
    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["gallery_root"] == str(gallery.resolve())
    assert body["thumb_dir"] == str(thumbs.resolve())
