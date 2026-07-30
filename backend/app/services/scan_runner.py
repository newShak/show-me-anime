"""统一扫描入口，供 API 与 watchdog 共用。"""

import threading

from app.db.models import ScanJob
from app.db.session import SessionLocal, get_engine
from app.services.album_reader import get_album_reader
from app.services.scanner import Scanner

_lock = threading.Lock()


def run_scan() -> ScanJob | None:
    """执行全量扫描；若已有扫描在进行则返回 None。"""
    if not _lock.acquire(blocking=False):
        return None
    try:
        db = SessionLocal(bind=get_engine())
        try:
            job = Scanner().scan_all(db)
        finally:
            db.close()
        get_album_reader().invalidate()
        return job
    finally:
        _lock.release()


def is_scan_running() -> bool:
    return _lock.locked()
