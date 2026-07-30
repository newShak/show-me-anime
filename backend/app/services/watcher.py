"""gallery 目录 watchdog 监听。"""

import logging
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config import get_settings
from app.services.scan_runner import run_scan

logger = logging.getLogger(__name__)


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds: float):
        self.debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, _event) -> None:
        self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._trigger_scan)
            self._timer.daemon = True
            self._timer.start()

    def _trigger_scan(self) -> None:
        job = run_scan()
        if job:
            logger.info("watchdog scan done: added=%s updated=%s removed=%s", job.added, job.updated, job.removed)


class GalleryWatcher:
    def __init__(self):
        self.settings = get_settings()
        self._observer: Observer | None = None

    def start(self) -> None:
        if not self.settings.watch_enabled:
            return
        handler = _DebouncedHandler(self.settings.watch_debounce_seconds)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.settings.gallery_root), recursive=True)
        self._observer.start()
        logger.info("watchdog started: %s", self.settings.gallery_root)

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
        logger.info("watchdog stopped")


_watcher: GalleryWatcher | None = None


def start_gallery_watcher() -> None:
    global _watcher
    if _watcher is not None:
        return
    _watcher = GalleryWatcher()
    _watcher.start()


def stop_gallery_watcher() -> None:
    global _watcher
    if _watcher is None:
        return
    _watcher.stop()
    _watcher = None
