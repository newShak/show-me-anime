"""外站下载任务（内存队列 + DB 记录，后台线程）。"""

import hashlib
import logging
import re
import threading
import time
import uuid
from pathlib import Path

from PIL import Image

from app.config import Settings, get_settings
from app.db.session import SessionLocal, get_engine
from app.db.models import DownloadRecord
from app.services.download.cache import (
    cleanup_job_cache,
    job_cache_dir,
    move_cache_files_to_dest,
)
from app.services.download.records import create_record, get_record, record_to_job, update_record
from app.services.download.registry import get_adapter
from app.services.download.types import DownloadJobState
from app.services.download.wnacg import _slug
from app.services.scan_runner import run_scan

logger = logging.getLogger(__name__)

_jobs: dict[str, DownloadJobState] = {}
_running_ids: set[str] = set()
_lock = threading.Lock()
_run_sem: threading.Semaphore | None = None
_run_sem_size = 0


def _safe_rel_path(raw: str) -> str:
    parts = []
    for seg in raw.replace("\\", "/").split("/"):
        seg = seg.strip().strip(".")
        if not seg or seg in {".", ".."}:
            continue
        parts.append(seg)
    return "/".join(parts)


def _run_semaphore() -> threading.Semaphore:
    global _run_sem, _run_sem_size
    size = max(1, get_settings().download_concurrency)
    if _run_sem is None or _run_sem_size != size:
        _run_sem = threading.Semaphore(size)
        _run_sem_size = size
    return _run_sem


def _persist(job_id: str, **kwargs) -> None:
    db = SessionLocal(bind=get_engine())
    try:
        update_record(db, job_id, **kwargs)
    finally:
        db.close()


def _insert_record(job: DownloadJobState) -> None:
    db = SessionLocal(bind=get_engine())
    try:
        create_record(db, job)
    finally:
        db.close()


def create_download_job(
    source: str,
    album_id: str,
    title: str,
    target_rel_path: str,
) -> DownloadJobState:
    rel = _safe_rel_path(target_rel_path)
    if not rel:
        raise ValueError("invalid target_rel_path")

    job = DownloadJobState(
        id=uuid.uuid4().hex[:12],
        source=source,
        album_id=album_id,
        title=title,
        target_rel_path=rel,
        status="pending",
    )
    with _lock:
        _jobs[job.id] = job
    _insert_record(job)
    threading.Thread(target=_run_job, args=(job.id,), daemon=True).start()
    return job


def get_job(job_id: str) -> DownloadJobState | None:
    with _lock:
        job = _jobs.get(job_id)
    if job is not None:
        return job
    db = SessionLocal(bind=get_engine())
    try:
        row = get_record(db, job_id)
        return record_to_job(row) if row else None
    finally:
        db.close()


def is_download_job_running(job_id: str) -> bool:
    with _lock:
        return job_id in _running_ids


def reconcile_stale_download_jobs(db) -> int:
    """将无运行线程的 pending/running 下载标记为已中断。"""
    rows = (
        db.query(DownloadRecord)
        .filter(DownloadRecord.status.in_(["pending", "running"]))
        .all()
    )
    stale = [r for r in rows if not is_download_job_running(r.id)]
    if not stale:
        return 0

    settings = get_settings()
    from app.services.download.transfer import is_job_resumable

    now = time.time()
    for row in stale:
        cache_dir = settings.download_cache_dir / row.id
        row.status = "failed"
        row.message = "任务已中断，可续传" if is_job_resumable(cache_dir) else "任务已中断"
        row.finished_at = now
        with _lock:
            _jobs.pop(row.id, None)

    db.commit()
    logger.info("reconciled %s stale download jobs", len(stale))
    return len(stale)


def _update(job_id: str, **kwargs) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            for key, val in kwargs.items():
                setattr(job, key, val)
    _persist(job_id, **kwargs)


def default_target_rel_path(source: str, title: str, album_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    base = _safe_rel_path(settings.download_default_subdir) or "imports/wnacg"
    return album_target_rel_path(base, title, album_id)


def album_target_rel_path(parent_rel_path: str, title: str, album_id: str) -> str:
    base = _safe_rel_path(parent_rel_path)
    folder = _slug(title) or album_id
    return f"{base}/{folder}" if base else folder


def create_download_jobs_batch(
    items: list[tuple[str, str, str]],
    parent_rel_path: str,
) -> list[DownloadJobState]:
    base = _safe_rel_path(parent_rel_path)
    used: set[str] = set()
    jobs: list[DownloadJobState] = []
    for source, album_id, title in items:
        folder = _slug(title) or album_id
        rel = f"{base}/{folder}" if base else folder
        if rel in used:
            suffix = album_id[-6:] if len(album_id) >= 6 else album_id
            rel = f"{base}/{folder}-{suffix}" if base else f"{folder}-{suffix}"
        used.add(rel)
        jobs.append(create_download_job(source, album_id, title, rel))
    return jobs


def resume_download_job(job_id: str) -> DownloadJobState:
    job = get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    if job.status == "done":
        raise ValueError("job already done")
    if job.status == "running" and is_download_job_running(job_id):
        raise ValueError("job already running")

    settings = get_settings()
    cache_dir = job_cache_dir(settings, job_id)
    from app.services.download.transfer import is_job_resumable

    if not is_job_resumable(cache_dir):
        raise ValueError("no resumable partial download")

    with _lock:
        _jobs[job_id] = job
    _update(job_id, status="pending", message="等待续传")
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return get_job(job_id) or job


def _run_job(job_id: str) -> None:
    sem = _run_semaphore()
    sem.acquire()
    job = get_job(job_id)
    if job is None:
        sem.release()
        return
    with _lock:
        _jobs[job_id] = job
        _running_ids.add(job_id)
    settings = get_settings()
    _update(job_id, status="running", progress=5, message="准备下载")
    try:
        adapter = get_adapter(job.source, settings)
        target = adapter.resolve_download(job.album_id)
        cache_dir = job_cache_dir(settings, job_id)
        dest_dir = (settings.gallery_root / job.target_rel_path).resolve()
        root = settings.gallery_root.resolve()
        if not str(dest_dir).startswith(str(root)):
            raise ValueError("target path escapes gallery root")

        if settings.download_use_mock or str(target.urls[0]).startswith("mock://"):
            _write_mock_images(cache_dir, job.title, job.album_id)
        elif target.kind == "images":
            _write_images(target.urls, cache_dir, job_id, len(target.urls), target.referer)
        else:
            _write_archive(target, cache_dir, job_id)

        saved = move_cache_files_to_dest(cache_dir, dest_dir)
        cleanup_job_cache(cache_dir)
        if saved == 0:
            raise ValueError("没有可写入画廊的文件")

        _update(job_id, progress=90, message="触发扫描", saved_files=saved)
        run_scan(source="download", changed_paths=[job.target_rel_path])
        _update(job_id, status="done", progress=100, message=f"已保存 {saved} 个文件", saved_files=saved)
        logger.info("download job_id=%s done path=%s files=%s", job_id, job.target_rel_path, saved)
    except Exception as exc:
        logger.exception("download job_id=%s failed: %s", job_id, exc)
        _update(job_id, status="failed", message=str(exc))
    finally:
        with _lock:
            _running_ids.discard(job_id)
        sem.release()


def _write_mock_images(dest_dir: Path, title: str, album_id: str) -> int:
    count = 3
    seed_base = int(hashlib.md5(album_id.encode()).hexdigest()[:8], 16)
    for i in range(1, count + 1):
        seed = seed_base + i
        color = ((seed * 40) % 200 + 30, (seed * 70) % 200 + 30, (seed * 110) % 200 + 30)
        img = Image.new("RGB", (800, 1200), color)
        img.save(dest_dir / f"{i:03d}.jpg", format="JPEG", quality=88)
    (dest_dir / ".mock-source.txt").write_text(f"mock wnacg {album_id} {title}\n", encoding="utf-8")
    return count


def _write_images(
    urls: list[str], dest_dir: Path, job_id: str, total: int, referer: str | None = None
) -> int:
    from app.services.download.http_client import download_client

    settings = get_settings()
    saved = 0
    headers = {"Referer": referer} if referer else {}
    from app.services.download.transfer import SpeedLimiter

    limiter = SpeedLimiter(settings.download_speed_limit_kbps)
    with download_client(settings) as client:
        for idx, url in enumerate(urls, start=1):
            res = client.get(url, headers=headers)
            res.raise_for_status()
            limiter.wait(len(res.content))
            ext = _guess_ext(url, res.headers.get("content-type"))
            (dest_dir / f"{idx:03d}{ext}").write_bytes(res.content)
            saved += 1
            pct = 5 + int(80 * saved / max(total, 1))
            _update(job_id, progress=pct, message=f"下载 {saved}/{total}")
    return saved


def _write_archive(target, dest_dir: Path, job_id: str) -> int:
    from app.services.download.http_client import download_client
    from app.services.download.transfer import (
        ZIP_NAME,
        clear_resume_meta,
        download_file_resumable,
        try_extract_or_none,
    )

    settings = get_settings()
    url = target.urls[0]
    zip_path = dest_dir / ZIP_NAME

    saved = try_extract_or_none(zip_path, dest_dir)
    if saved is not None:
        _update(job_id, progress=75, message="解压中")
        zip_path.unlink(missing_ok=True)
        clear_resume_meta(dest_dir)
        if saved == 0:
            raise ValueError("压缩包内没有可用文件")
        return saved

    partial = zip_path.stat().st_size if zip_path.is_file() else 0
    _update(job_id, progress=15, message=f"续传下载 ({partial // 1024}KB)" if partial else "下载压缩包")

    def on_progress(done: int, total: int | None) -> None:
        if total and total > 0:
            pct = 15 + int(55 * done / total)
            msg = f"续传 {done // 1024}KB/{total // 1024}KB" if partial else "下载压缩包"
            _update(job_id, progress=pct, message=msg)

    with download_client(settings) as client:
        download_file_resumable(
            client,
            url,
            target.referer,
            zip_path,
            target.file_key,
            on_progress,
            settings.download_speed_limit_kbps,
        )

    _update(job_id, progress=75, message="解压中")
    saved = try_extract_or_none(zip_path, dest_dir)
    if saved is None:
        raise ValueError("压缩包损坏或不完整")
    zip_path.unlink(missing_ok=True)
    clear_resume_meta(dest_dir)
    if saved == 0:
        raise ValueError("压缩包内没有可用文件")
    return saved


def _guess_ext(url: str, content_type: str | None) -> str:
    if content_type and "jpeg" in content_type:
        return ".jpg"
    if content_type and "png" in content_type:
        return ".png"
    if content_type and "webp" in content_type:
        return ".webp"
    m = re.search(r"\.(jpe?g|png|webp)(?:\?|$)", url, re.I)
    return f".{m.group(1).lower()}" if m else ".jpg"
