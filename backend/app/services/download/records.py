"""外站下载记录持久化。"""

import json
import time

from sqlalchemy.orm import Session

from app.db.models import DownloadRecord
from app.services.download.types import DownloadJobState


def _dump_int_list(items: list[int]) -> str:
    return json.dumps(items, ensure_ascii=False)


def _dump_str_list(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def _load_int_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [int(x) for x in data if isinstance(x, int) or str(x).isdigit()]


def _load_str_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip() for x in data if str(x).strip()]


def create_record(db: Session, job: DownloadJobState) -> None:
    now = time.time()
    row = DownloadRecord(
        id=job.id,
        source=job.source,
        album_id=job.album_id,
        title=job.title,
        target_rel_path=job.target_rel_path,
        status=job.status,
        progress=job.progress,
        message=job.message,
        saved_files=job.saved_files,
        skipped_files=job.skipped_files,
        target_existed=job.target_existed,
        tag_ids_json=_dump_int_list(job.tag_ids),
        import_remote_tags_json=_dump_str_list(job.import_remote_tags),
        created_at=now,
        finished_at=None,
    )
    db.add(row)
    db.commit()


def update_record(db: Session, job_id: str, **kwargs) -> None:
    row = db.get(DownloadRecord, job_id)
    if row is None:
        return
    for key, val in kwargs.items():
        setattr(row, key, val)
    if kwargs.get("status") in {"done", "failed"}:
        row.finished_at = time.time()
    elif kwargs.get("status") in {"pending", "running"}:
        row.finished_at = None
    db.commit()


def get_record(db: Session, job_id: str) -> DownloadRecord | None:
    return db.get(DownloadRecord, job_id)


def list_records(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[DownloadRecord], int]:
    q = db.query(DownloadRecord).order_by(DownloadRecord.created_at.desc())
    if status:
        q = q.filter(DownloadRecord.status == status)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def delete_record(db: Session, job_id: str) -> bool:
    row = db.get(DownloadRecord, job_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def record_to_job(row: DownloadRecord) -> DownloadJobState:
    return DownloadJobState(
        id=row.id,
        source=row.source,
        album_id=row.album_id,
        title=row.title,
        target_rel_path=row.target_rel_path,
        status=row.status,
        progress=row.progress,
        message=row.message,
        saved_files=row.saved_files,
        skipped_files=row.skipped_files,
        target_existed=row.target_existed,
        tag_ids=_load_int_list(row.tag_ids_json),
        import_remote_tags=_load_str_list(row.import_remote_tags_json),
    )
