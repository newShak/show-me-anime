"""统一扫描入口，供 API 与 watchdog 共用。"""

import logging
import threading
import time

from app import constants
from app.db.models import ScanJob
from app.db.session import SessionLocal, get_engine
from app.services.album_reader import get_album_reader
from app.services.scanner import Scanner

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def _scan_hint_paths(changed_paths: list[str] | None, limit: int = 10) -> str:
    if not changed_paths:
        return "[]"
    unique = list(dict.fromkeys(changed_paths))
    if len(unique) <= limit:
        return str(unique)
    head = ", ".join(repr(p) for p in unique[:limit])
    return f"[{head}, ... +{len(unique) - limit} more]"


def run_scan(
    source: str = "manual",
    changed_paths: list[str] | None = None,
    mode: str = constants.SCAN_MODE_INCREMENTAL,
) -> ScanJob | None:
    """执行扫描；若已有扫描在进行则返回 None。"""
    if not _lock.acquire(blocking=False):
        logger.warning("scan skipped source=%s reason=lock_held", source)
        return None

    logger.info("scan started source=%s mode=%s hints=%s paths=%s", source, mode, len(changed_paths or []), _scan_hint_paths(changed_paths))
    started = time.time()
    try:
        db = SessionLocal(bind=get_engine())
        try:
            job = Scanner().scan_all(db, source=source, changed_paths=changed_paths, mode=mode)
        finally:
            db.close()
        get_album_reader().invalidate()
        logger.info(
            "scan finished source=%s job_id=%s added=%s updated=%s removed=%s duration=%.2fs",
            source,
            job.id,
            job.added,
            job.updated,
            job.removed,
            time.time() - started,
        )
        return job
    except Exception:
        logger.exception("scan failed source=%s duration=%.2fs", source, time.time() - started)
        raise
    finally:
        _lock.release()


def is_scan_running() -> bool:
    return _lock.locked()
