"""gallery 目录 watchdog 监听。"""

import logging
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config import get_settings
from app.services.scan_runner import is_scan_running, run_scan

logger = logging.getLogger(__name__)


def _unique_paths(paths: list[str]) -> list[str]:
    """去重并保持顺序。"""
    return list(dict.fromkeys(p for p in paths if p))


def _format_paths(paths: list[str], limit: int = 10) -> str:
    unique = _unique_paths(paths)
    if not unique:
        return "[]"
    if len(unique) <= limit:
        return str(unique)
    head = ", ".join(repr(p) for p in unique[:limit])
    return f"[{head}, ... +{len(unique) - limit} more]"


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds: float):
        self.debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._pending_paths: list[str] = []
        self._cooldown_until = 0.0

    def _scan_busy(self) -> bool:
        return is_scan_running() or time.time() < self._cooldown_until

    def on_any_event(self, event) -> None:
        src = getattr(event, "src_path", None)
        dest = getattr(event, "dest_path", None)
        if self._scan_busy():
            logger.debug(
                "watchdog event ignored type=%s src=%s dest=%s reason=%s",
                getattr(event, "event_type", "?"),
                src,
                dest,
                "scan_running" if is_scan_running() else "cooldown",
            )
            return
        if src:
            self._pending_paths.append(src)
        if dest:
            self._pending_paths.append(dest)
        logger.debug(
            "watchdog event type=%s src=%s dest=%s pending=%s",
            getattr(event, "event_type", "?"),
            src,
            dest,
            len(self._pending_paths),
        )
        self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._scan_busy():
                return
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._trigger_scan)
            self._timer.daemon = True
            self._timer.start()
        logger.debug("watchdog event debounced %.1fs", self.debounce_seconds)

    def _trigger_scan(self) -> None:
        if self._scan_busy():
            return
        with self._lock:
            paths = self._pending_paths[:]
            self._pending_paths.clear()
        unique = _unique_paths(paths)
        logger.info(
            "watchdog debounced scan triggered hints=%s paths=%s",
            len(unique),
            _format_paths(unique),
        )
        job = run_scan(source="watchdog", changed_paths=unique or None)
        if job is None:
            logger.warning("watchdog scan skipped reason=concurrent_scan")
            return
        self._cooldown_until = time.time() + self.debounce_seconds


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
