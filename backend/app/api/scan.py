"""扫描 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import constants
from app.db.models import ScanJob
from app.db.session import get_db
from app.schemas.scan import ScanJobResponse
from app.services.album_reader import get_album_reader
from app.services.scanner import Scanner

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/trigger", response_model=ScanJobResponse)
def trigger_scan(db: Session = Depends(get_db)) -> ScanJob:
    running = db.query(ScanJob).filter(ScanJob.status == constants.SCAN_RUNNING).first()
    if running:
        raise HTTPException(status_code=409, detail="scan already running")

    job = Scanner().scan_all(db)
    get_album_reader().invalidate()
    return job


@router.get("/status", response_model=ScanJobResponse | None)
def scan_status(db: Session = Depends(get_db)) -> ScanJob | None:
    return db.query(ScanJob).order_by(ScanJob.id.desc()).first()
