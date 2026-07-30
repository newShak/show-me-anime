"""watchdog 事件过滤测试。"""

from watchdog.events import (
    DirCreatedEvent,
    FileClosedEvent,
    FileClosedNoWriteEvent,
    FileOpenedEvent,
)

from app.services.watcher import _DebouncedHandler, _is_read_only_access


def test_read_only_event_types():
    assert _is_read_only_access(FileOpenedEvent("/data/gallery/a.jpg"))
    assert _is_read_only_access(FileClosedNoWriteEvent("/data/gallery/a.jpg"))
    assert not _is_read_only_access(FileClosedEvent("/data/gallery/a.jpg"))
    assert not _is_read_only_access(DirCreatedEvent("/data/gallery/new-album"))


def test_ignore_read_only_events():
    handler = _DebouncedHandler(debounce_seconds=1)
    handler.on_any_event(FileOpenedEvent("/data/gallery/album/page.jpg"))
    handler.on_any_event(FileClosedNoWriteEvent("/data/gallery/album/page.jpg"))
    assert handler._pending_paths == []


def test_collect_directory_created_event():
    handler = _DebouncedHandler(debounce_seconds=1)
    handler.on_any_event(DirCreatedEvent("/data/gallery/new-album"))
    assert handler._pending_paths == ["/data/gallery/new-album"]
