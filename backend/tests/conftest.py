"""pytest 公共 fixture。"""

import pytest
from fastapi.testclient import TestClient

from app.config import reload_settings
from app.db.session import init_db, reset_engine
from app.main import app
from app.services.album_reader import reset_album_reader


@pytest.fixture(autouse=True)
def _reset_app_state(tmp_path, monkeypatch):
    gallery = tmp_path / "gallery"
    thumbs = tmp_path / "thumbs"
    gallery.mkdir()
    thumbs.mkdir()
    db_path = tmp_path / "test.db"
    settings_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.SETTINGS_JSON", settings_json)
    monkeypatch.setattr("app.config._load_yaml_overrides", lambda: {})
    monkeypatch.setenv("WATCH_ENABLED", "false")
    monkeypatch.setenv("GALLERY_ROOT", str(gallery))
    monkeypatch.setenv("THUMB_DIR", str(thumbs))
    monkeypatch.setenv("DOWNLOAD_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reload_settings()
    reset_engine()
    reset_album_reader()
    init_db()
    yield
    reset_engine()
    reset_album_reader()
    reload_settings()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def gallery():
    from app.config import get_settings

    return get_settings().gallery_root
