"""外站下载 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.download import (
    DownloadCacheClearResponse,
    DownloadJobCreate,
    DownloadJobBatchCreate,
    DownloadJobBatchResponse,
    DownloadJobResponse,
    DownloadOptionsResponse,
    DownloadRecordListResponse,
    DownloadRecordResponse,
    DownloadSourceResponse,
    ProxyTestResponse,
    RemoteDetailResponse,
    RemotePreviewBatchResponse,
    RemoteSearchResponse,
    RemoteBrowseResponse,
    BrowseNavItemResponse,
    RemoteAlbumResponse,
)
from app.services.download.cache import clear_download_cache
from app.services.download.http_client import probe_proxy
from app.services.download.jobs import (
    create_download_job,
    create_download_jobs_batch,
    default_target_rel_path,
    delete_download_record,
    get_job,
    is_download_job_running,
    overwrite_download_job,
    reconcile_stale_download_jobs,
    resume_download_job,
    retry_download_job,
    _safe_rel_path,
)
from app.services.download.records import list_records
from app.services.download.registry import get_adapter, list_sources
from app.services.download.transfer import is_job_resumable
from sqlalchemy.orm import Session

router = APIRouter(prefix="/download", tags=["download"])

_RECORD_STATUS = frozenset({"pending", "running", "done", "failed"})


def _job_response(job) -> DownloadJobResponse:
    return DownloadJobResponse(
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
    )


def _album(a) -> RemoteAlbumResponse:
    return RemoteAlbumResponse(
        source=a.source,
        id=a.id,
        title=a.title,
        cover_url=a.cover_url,
        page_count=a.page_count,
        category=a.category,
        language=a.language,
        tags=a.tags,
    )


def _nav_item(n) -> BrowseNavItemResponse:
    return BrowseNavItemResponse(
        label=n.label,
        cate_id=n.cate_id,
        children=[_nav_item(c) for c in n.children],
    )


@router.get("/sources", response_model=list[DownloadSourceResponse])
def download_sources(settings: Settings = Depends(get_settings)) -> list[DownloadSourceResponse]:
    return [DownloadSourceResponse(**item) for item in list_sources(settings)]


@router.get("/options", response_model=DownloadOptionsResponse)
def download_options(settings: Settings = Depends(get_settings)) -> DownloadOptionsResponse:
    return DownloadOptionsResponse(
        preview_batch_size=settings.download_preview_batch_size,
        concurrency=settings.download_concurrency,
    )


@router.get("/records", response_model=DownloadRecordListResponse)
def download_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DownloadRecordListResponse:
    if status is not None and status not in _RECORD_STATUS:
        raise HTTPException(status_code=400, detail="invalid status")
    reconcile_stale_download_jobs(db)
    rows, total = list_records(db, page, page_size, status)
    return DownloadRecordListResponse(
        items=[
            DownloadRecordResponse(
                id=r.id,
                source=r.source,
                album_id=r.album_id,
                title=r.title,
                target_rel_path=r.target_rel_path,
                status=r.status,
                progress=r.progress,
                message=r.message,
                saved_files=r.saved_files,
                skipped_files=r.skipped_files,
                target_existed=r.target_existed,
                created_at=r.created_at,
                finished_at=r.finished_at,
                resumable=r.status == "failed"
                and not is_download_job_running(r.id)
                and is_job_resumable(settings.download_cache_dir / r.id),
                can_overwrite=r.status == "done"
                and not is_download_job_running(r.id)
                and (r.target_existed or r.skipped_files > 0),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/records/{job_id}", status_code=204)
def remove_download_record(job_id: str) -> Response:
    try:
        delete_download_record(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/search", response_model=RemoteSearchResponse)
def download_search(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=48, alias="pageSize"),
    source: str = Query(default="wnacg"),
    settings: Settings = Depends(get_settings),
) -> RemoteSearchResponse:
    try:
        adapter = get_adapter(source, settings)
        result = adapter.search(q, page, page_size)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return RemoteSearchResponse(
        items=[_album(a) for a in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/browse", response_model=RemoteBrowseResponse)
def download_browse(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=48, alias="pageSize"),
    cate_id: int | None = Query(default=None, alias="cateId"),
    source: str = Query(default="wnacg"),
    settings: Settings = Depends(get_settings),
) -> RemoteBrowseResponse:
    try:
        adapter = get_adapter(source, settings)
        browse = getattr(adapter, "browse", None)
        if browse is None:
            raise NotImplementedError("browse not supported")
        result = browse(cate_id, page, page_size)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return RemoteBrowseResponse(
        items=[_album(a) for a in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        cate_id=result.cate_id,
        title=result.title,
        nav=[_nav_item(n) for n in result.nav],
    )


@router.get("/detail", response_model=RemoteDetailResponse)
def download_detail(
    id: str = Query(..., alias="id"),
    source: str = Query(default="wnacg"),
    settings: Settings = Depends(get_settings),
) -> RemoteDetailResponse:
    try:
        adapter = get_adapter(source, settings)
        detail = adapter.get_detail(id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    rel = default_target_rel_path(source, detail.title, detail.id, settings)
    parent = _safe_rel_path(settings.download_default_subdir) or "imports/wnacg"
    return RemoteDetailResponse(
        source=detail.source,
        id=detail.id,
        title=detail.title,
        page_count=detail.page_count,
        cover_url=detail.cover_url,
        preview_urls=detail.preview_urls,
        preview_has_more=detail.preview_has_more,
        preview_total=detail.preview_total,
        category=detail.category,
        language=detail.language,
        tags=detail.tags,
        default_target_rel_path=rel,
        default_parent_rel_path=parent,
    )


@router.get("/previews", response_model=RemotePreviewBatchResponse)
def download_previews(
    id: str = Query(..., alias="id"),
    source: str = Query(default="wnacg"),
    offset: int = Query(default=0, ge=0),
    limit: int | None = Query(default=None, ge=1, le=50, alias="limit"),
    settings: Settings = Depends(get_settings),
) -> RemotePreviewBatchResponse:
    batch_size = limit or settings.download_preview_batch_size
    try:
        adapter = get_adapter(source, settings)
        batch = adapter.get_preview_batch(id, offset, batch_size)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail="preview batch not supported") from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return RemotePreviewBatchResponse(
        preview_urls=batch.preview_urls,
        offset=batch.offset,
        count=batch.count,
        total=batch.total,
        has_more=batch.has_more,
    )


@router.get("/cover")
def download_cover(
    id: str = Query(..., alias="id"),
    source: str = Query(default="wnacg"),
    settings: Settings = Depends(get_settings),
):
    try:
        adapter = get_adapter(source, settings)
        data, media_type = adapter.fetch_cover_bytes(id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"cover fetch failed: {exc}") from exc
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/preview")
def download_preview(
    id: str = Query(..., alias="id"),
    n: int = Query(default=0, ge=0, alias="n"),
    source: str = Query(default="wnacg"),
    settings: Settings = Depends(get_settings),
):
    try:
        adapter = get_adapter(source, settings)
        data, media_type = adapter.fetch_preview_bytes(id, n)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"preview fetch failed: {exc}") from exc
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "private, max-age=3600"})


@router.post("/jobs", response_model=DownloadJobResponse)
def start_download_job(body: DownloadJobCreate) -> DownloadJobResponse:
    try:
        job = create_download_job(body.source, body.album_id, body.title, body.target_rel_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_response(job)


@router.post("/jobs/batch", response_model=DownloadJobBatchResponse)
def start_download_jobs_batch(body: DownloadJobBatchCreate) -> DownloadJobBatchResponse:
    try:
        items = [(i.source, i.album_id, i.title) for i in body.items]
        jobs = create_download_jobs_batch(items, body.parent_rel_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DownloadJobBatchResponse(jobs=[_job_response(j) for j in jobs])


@router.get("/jobs/{job_id}", response_model=DownloadJobResponse)
def get_download_job(job_id: str, db: Session = Depends(get_db)) -> DownloadJobResponse:
    reconcile_stale_download_jobs(db)
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _job_response(job)


@router.post("/jobs/{job_id}/resume", response_model=DownloadJobResponse)
def resume_download_job_api(job_id: str) -> DownloadJobResponse:
    try:
        job = resume_download_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_response(job)


@router.post("/jobs/{job_id}/retry", response_model=DownloadJobResponse)
def retry_download_job_api(job_id: str) -> DownloadJobResponse:
    try:
        job = retry_download_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_response(job)


@router.post("/jobs/{job_id}/overwrite", response_model=DownloadJobResponse)
def overwrite_download_job_api(job_id: str) -> DownloadJobResponse:
    try:
        job = overwrite_download_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_response(job)


@router.post("/cache/clear", response_model=DownloadCacheClearResponse)
def clear_cache(settings: Settings = Depends(get_settings)) -> DownloadCacheClearResponse:
    try:
        deleted = clear_download_cache(settings)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    msg = f"已清空 {deleted} 项缓存" if deleted else "缓存目录已是空的"
    return DownloadCacheClearResponse(deleted=deleted, message=msg)


@router.post("/proxy/test", response_model=ProxyTestResponse)
def test_download_proxy(settings: Settings = Depends(get_settings)) -> ProxyTestResponse:
    ok, message = probe_proxy(settings)
    return ProxyTestResponse(ok=ok, message=message)
