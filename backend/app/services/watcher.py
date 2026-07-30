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
        self._pending_paths: list[str] = []

    def on_any_event(self, event) -> None:
        src = getattr(event, "src_path", None)
        if src:
            self._pending_paths.append(src)
        dest = getattr(event, "dest_path", None)
        if dest:
            self._pending_paths.append(dest)
        self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._trigger_scan)
            self._timer.daemon = True
            self._timer.start()
        logger.debug("watchdog event debounced %.1fs", self.debounce_seconds)

    def _trigger_scan(self) -> None:
        with self._lock:
            paths = self._pending_paths[:]
            self._pending_paths.clear()
        logger.info("watchdog debounced scan triggered hints=%s", len(paths))
        job = run_scan(source="watchdog", changed_paths=paths or None)
        if job is None:
            logger.warning("watchdog scan skipped reason=concurrent_scan")


class GalleryWatcher:
    def __init__(self):
        self.settings = get_settings()
        self._observer: Observer | None = None

    def start(self) -> None:
        if not self.settings.watch_enabled:
            logger.info("watchdog disabled watch_enabled=false")
            return
        handler = _DebouncedHandler(self.settings.watch_debounce_seconds)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.settings.gallery_root), recursive=True)
        self._observer.start()
        logger.info("watchdog started root=%s debounce=%ss", self.settings.gallery_root, self.settings.watch_debounce_seconds)

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
        logger.debug("watchdog already running")
        return
    _watcher = GalleryWatcher()
    _watcher.start()


def stop_gallery_watcher() -> None:
    global _watcher
    if _watcher is None:
        return
    _watcher.stop()
    _watcher = None
