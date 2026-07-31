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
from app.services.download.types import DownloadCancelled, DownloadJobState
from app.services.download.wnacg import _slug
from app.services.scan_runner import run_scan

logger = logging.getLogger(__name__)

_jobs: dict[str, DownloadJobState] = {}
_running_ids: set[str] = set()
_force_overwrite: set[str] = set()
_cancel_ids: set[str] = set()
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


def _dest_dir(settings: Settings, target_rel_path: str) -> Path:
    dest = (settings.gallery_root / target_rel_path).resolve()
    root = settings.gallery_root.resolve()
    if not str(dest).startswith(str(root)):
        raise ValueError("target path escapes gallery root")
    return dest


def target_path_exists(settings: Settings, target_rel_path: str) -> bool:
    """目标目录已存在且含非隐藏内容时视为占用。"""
    dest = _dest_dir(settings, target_rel_path)
    if not dest.is_dir():
        return False
    return any(not item.name.startswith(".") for item in dest.iterdir())


def count_dest_files(dest_dir: Path) -> int:
    if not dest_dir.is_dir():
        return 0
    return sum(1 for item in dest_dir.iterdir() if item.is_file() and not item.name.startswith("."))


def _is_cancelled(job_id: str) -> bool:
    with _lock:
        return job_id in _cancel_ids


def _check_cancel(job_id: str) -> None:
    if _is_cancelled(job_id):
        raise DownloadCancelled()


def _clear_cancel(job_id: str) -> None:
    with _lock:
        _cancel_ids.discard(job_id)


def _finish_message(saved: int, skipped: int) -> str:
    if saved and skipped:
        return f"已保存 {saved} 个文件，跳过 {skipped} 个已存在"
    if skipped and not saved:
        return f"跳过 {skipped} 个已存在文件，未新增"
    return f"已保存 {saved} 个文件"


def create_download_job(
    source: str,
    album_id: str,
    title: str,
    target_rel_path: str,
) -> DownloadJobState:
    rel = _safe_rel_path(target_rel_path)
    if not rel:
        raise ValueError("invalid target_rel_path")

    settings = get_settings()
    existed = target_path_exists(settings, rel)
    job = DownloadJobState(
        id=uuid.uuid4().hex[:12],
        source=source,
        album_id=album_id,
        title=title,
        target_rel_path=rel,
        status="pending",
        target_existed=existed,
        message="目标路径已存在，将跳过下载" if existed else None,
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


def retry_download_job(job_id: str) -> DownloadJobState:
    """重试失败任务：有断点则续传，否则清空缓存后重新下载。"""
    job = get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    if job.status == "done":
        raise ValueError("job already done")
    if is_download_job_running(job_id):
        raise ValueError("job already running")
    if job.status != "failed":
        raise ValueError("job cannot be retried")

    settings = get_settings()
    cache_dir = job_cache_dir(settings, job_id)
    from app.services.download.transfer import is_job_resumable

    if is_job_resumable(cache_dir):
        message = "等待续传"
    else:
        cleanup_job_cache(cache_dir)
        message = "等待重试"

    with _lock:
        _jobs[job_id] = job
        _force_overwrite.discard(job_id)
        _cancel_ids.discard(job_id)
    _update(job_id, status="pending", progress=0, message=message, saved_files=0, skipped_files=0)
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return get_job(job_id) or job


def cancel_download_job(job_id: str) -> DownloadJobState:
    """中断等待中或进行中的下载任务。"""
    job = get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    if job.status not in {"pending", "running"}:
        raise ValueError("job cannot be cancelled")
    with _lock:
        _cancel_ids.add(job_id)
    if job.status == "pending":
        _update(job_id, status="failed", progress=0, message="已取消")
    else:
        _update(job_id, message="正在取消…")
    return get_job(job_id) or job


def overwrite_download_job(job_id: str) -> DownloadJobState:
    """强制覆盖：重新下载并覆盖目标目录已有文件。"""
    job = get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    if is_download_job_running(job_id):
        raise ValueError("job already running")
    if job.status != "done":
        raise ValueError("job cannot be overwritten")
    if not job.target_existed and job.skipped_files <= 0:
        raise ValueError("job has nothing to overwrite")

    settings = get_settings()
    cleanup_job_cache(job_cache_dir(settings, job_id))
    with _lock:
        _jobs[job_id] = job
        _force_overwrite.add(job_id)
        _cancel_ids.discard(job_id)
    _update(
        job_id,
        status="pending",
        progress=0,
        message="等待强制覆盖",
        saved_files=0,
        skipped_files=0,
    )
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return get_job(job_id) or job


def resume_download_job(job_id: str) -> DownloadJobState:
    return retry_download_job(job_id)


def delete_download_record(job_id: str) -> None:
    """删除下载记录并清理缓存；进行中的任务不可删。"""
    if is_download_job_running(job_id):
        raise ValueError("job is running")
    job = get_job(job_id)
    if job is None:
        raise ValueError("job not found")
    if job.status in {"pending", "running"}:
        raise ValueError("job is running")

    settings = get_settings()
    cleanup_job_cache(job_cache_dir(settings, job_id))
    with _lock:
        _jobs.pop(job_id, None)
        _running_ids.discard(job_id)
        _force_overwrite.discard(job_id)
        _cancel_ids.discard(job_id)

    from app.services.download.records import delete_record

    db = SessionLocal(bind=get_engine())
    try:
        if not delete_record(db, job_id):
            raise ValueError("job not found")
    finally:
        db.close()


def _take_force_overwrite(job_id: str) -> bool:
    with _lock:
        if job_id in _force_overwrite:
            _force_overwrite.discard(job_id)
            return True
        return False


def _run_job(job_id: str) -> None:
    sem = _run_semaphore()
    with _lock:
        _running_ids.add(job_id)
    try:
        sem.acquire()
        _check_cancel(job_id)
        job = get_job(job_id)
        if job is None:
            return
        with _lock:
            _jobs[job_id] = job
        settings = get_settings()
        overwrite = _take_force_overwrite(job_id)
        dest_dir = _dest_dir(settings, job.target_rel_path)
        existed = job.target_existed or target_path_exists(settings, job.target_rel_path)
        if existed and not overwrite:
            skipped = count_dest_files(dest_dir)
            _update(
                job_id,
                status="done",
                progress=100,
                message="目标路径已存在，已跳过",
                saved_files=0,
                skipped_files=skipped,
                target_existed=True,
            )
            logger.info(
                "download job_id=%s skipped existing path=%s files=%s",
                job_id,
                job.target_rel_path,
                skipped,
            )
            return
        _update(job_id, status="running", progress=5, message="准备下载", target_existed=existed)
        _check_cancel(job_id)
        adapter = get_adapter(job.source, settings)
        target = adapter.resolve_download(job.album_id)
        _check_cancel(job_id)
        cache_dir = job_cache_dir(settings, job_id)
        pre_skipped = 0

        if settings.download_use_mock or str(target.urls[0]).startswith("mock://"):
            pre_skipped = _write_mock_images(cache_dir, job.title, job.album_id, dest_dir, overwrite)
        elif target.kind == "images":
            pre_skipped = _write_images(
                target.urls, cache_dir, dest_dir, job_id, len(target.urls), target.referer, overwrite
            )
        else:
            _write_archive(target, cache_dir, job_id, overwrite, lambda: _check_cancel(job_id))

        move = move_cache_files_to_dest(cache_dir, dest_dir, overwrite=overwrite)
        cleanup_job_cache(cache_dir)
        saved = move.saved
        skipped = move.skipped + pre_skipped
        if saved == 0 and skipped == 0:
            raise ValueError("没有可写入画廊的文件")

        msg = _finish_message(saved, skipped)
        _update(job_id, progress=90, message="触发扫描", saved_files=saved, skipped_files=skipped)
        run_scan(source="download", changed_paths=[job.target_rel_path])
        _update(
            job_id,
            status="done",
            progress=100,
            message=msg,
            saved_files=saved,
            skipped_files=skipped,
            target_existed=existed,
        )
        logger.info(
            "download job_id=%s done path=%s saved=%s skipped=%s",
            job_id,
            job.target_rel_path,
            saved,
            skipped,
        )
    except DownloadCancelled:
        settings = get_settings()
        cleanup_job_cache(job_cache_dir(settings, job_id))
        _update(job_id, status="failed", progress=0, message="已取消")
        logger.info("download job_id=%s cancelled", job_id)
    except Exception as exc:
        logger.exception("download job_id=%s failed: %s", job_id, exc)
        _update(job_id, status="failed", message=str(exc))
    finally:
        with _lock:
            _running_ids.discard(job_id)
            _force_overwrite.discard(job_id)
            _cancel_ids.discard(job_id)
        sem.release()


def _write_mock_images(
    cache_dir: Path, title: str, album_id: str, dest_dir: Path, overwrite: bool
) -> int:
    count = 3
    skipped = 0
    seed_base = int(hashlib.md5(album_id.encode()).hexdigest()[:8], 16)
    for i in range(1, count + 1):
        name = f"{i:03d}.jpg"
        if not overwrite and (dest_dir / name).is_file():
            skipped += 1
            continue
        seed = seed_base + i
        color = ((seed * 40) % 200 + 30, (seed * 70) % 200 + 30, (seed * 110) % 200 + 30)
        img = Image.new("RGB", (800, 1200), color)
        img.save(cache_dir / name, format="JPEG", quality=88)
    (cache_dir / ".mock-source.txt").write_text(f"mock wnacg {album_id} {title}\n", encoding="utf-8")
    return skipped


def _write_images(
    urls: list[str],
    cache_dir: Path,
    dest_dir: Path,
    job_id: str,
    total: int,
    referer: str | None,
    overwrite: bool,
) -> int:
    from app.services.download.http_client import download_client
    from app.services.download.transfer import SpeedLimiter

    settings = get_settings()
    headers = {"Referer": referer} if referer else {}
    limiter = SpeedLimiter(settings.download_speed_limit_kbps)
    fetched = skipped = 0
    with download_client(settings) as client:
        for idx, url in enumerate(urls, start=1):
            _check_cancel(job_id)
            ext = _guess_ext(url, None)
            name = f"{idx:03d}{ext}"
            if not overwrite and (dest_dir / name).is_file():
                skipped += 1
                continue
            res = client.get(url, headers=headers)
            res.raise_for_status()
            ext = _guess_ext(url, res.headers.get("content-type"))
            name = f"{idx:03d}{ext}"
            limiter.wait(len(res.content))
            (cache_dir / name).write_bytes(res.content)
            fetched += 1
            pct = 5 + int(80 * fetched / max(total, 1))
            _update(job_id, progress=pct, message=f"下载 {fetched}/{total}")
    return skipped


def _write_archive(
    target,
    cache_dir: Path,
    job_id: str,
    overwrite: bool,
    should_cancel,
) -> None:
    from app.services.download.http_client import download_client
    from app.services.download.transfer import (
        ZIP_NAME,
        clear_resume_meta,
        download_file_resumable,
        try_extract_or_none,
    )

    settings = get_settings()
    url = target.urls[0]
    zip_path = cache_dir / ZIP_NAME

    extracted = try_extract_or_none(zip_path, cache_dir, overwrite=overwrite)
    if extracted is not None:
        saved, skipped = extracted
        _update(job_id, progress=75, message="解压中")
        zip_path.unlink(missing_ok=True)
        clear_resume_meta(cache_dir)
        if saved == 0 and skipped == 0:
            raise ValueError("压缩包内没有可用文件")
        return

    partial = zip_path.stat().st_size if zip_path.is_file() else 0
    _update(job_id, progress=15, message=f"续传下载 ({partial // 1024}KB)" if partial else "下载压缩包")

    def on_progress(done: int, total: int | None) -> None:
        should_cancel()
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
            should_cancel=should_cancel,
        )

    _update(job_id, progress=75, message="解压中")
    extracted = try_extract_or_none(zip_path, cache_dir, overwrite=overwrite)
    if extracted is None:
        raise ValueError("压缩包损坏或不完整")
    saved, skipped = extracted
    zip_path.unlink(missing_ok=True)
    clear_resume_meta(cache_dir)
    if saved == 0 and skipped == 0:
        raise ValueError("压缩包内没有可用文件")


def _guess_ext(url: str, content_type: str | None) -> str:
    if content_type and "jpeg" in content_type:
        return ".jpg"
    if content_type and "png" in content_type:
        return ".png"
    if content_type and "webp" in content_type:
        return ".webp"
    m = re.search(r"\.(jpe?g|png|webp)(?:\?|$)", url, re.I)
    return f".{m.group(1).lower()}" if m else ".jpg"
