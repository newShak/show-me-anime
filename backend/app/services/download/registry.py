"""注册外站适配器。"""

from app.config import Settings, get_settings
from app.services.download.wnacg import WnacgAdapter

_ADAPTERS: dict[str, type[WnacgAdapter]] = {
    WnacgAdapter.source_id: WnacgAdapter,
}


def list_sources(settings: Settings | None = None) -> list[dict[str, str | bool]]:
    settings = settings or get_settings()
    return [
        {
            "id": cls.source_id,
            "name": cls.display_name,
            "mock": settings.download_use_mock and cls.source_id == "wnacg",
        }
        for cls in _ADAPTERS.values()
    ]


def get_adapter(source: str, settings: Settings | None = None):
    cls = _ADAPTERS.get(source)
    if cls is None:
        raise KeyError(f"unknown download source: {source}")
    return cls(settings or get_settings())
