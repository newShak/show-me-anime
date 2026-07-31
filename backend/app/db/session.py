"""数据库连接与会话。"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

logger = logging.getLogger(__name__)

_engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
        )
        event.listen(_engine, "connect", _set_sqlite_pragma)
    return _engine


def init_db() -> None:
    engine = get_engine()
    logger.info("initializing database url=%s", get_settings().database_url)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _migrate_schema(conn)
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                    node_id UNINDEXED,
                    title,
                    path,
                    tags,
                    tokenize = 'unicode61'
                )
                """
            )
        )
        conn.commit()
    logger.info("database ready")


def _migrate_schema(conn) -> None:
    """轻量 schema 迁移（SQLite 无 Alembic 时使用）。"""
    cols = {row[1] for row in conn.execute(text("PRAGMA table_info(nodes)")).fetchall()}
    if "subdir_count" not in cols:
        logger.info("migrating schema: add nodes.subdir_count")
        conn.execute(text("ALTER TABLE nodes ADD COLUMN subdir_count INTEGER DEFAULT 0"))
    if "archive_count" not in cols:
        logger.info("migrating schema: add nodes.archive_count")
        conn.execute(text("ALTER TABLE nodes ADD COLUMN archive_count INTEGER DEFAULT 0"))
    if "cover_manual" not in cols:
        logger.info("migrating schema: add nodes.cover_manual")
        conn.execute(text("ALTER TABLE nodes ADD COLUMN cover_manual INTEGER DEFAULT 0"))

    scan_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(scan_jobs)")).fetchall()}
    if scan_cols and "source" not in scan_cols:
        logger.info("migrating schema: add scan_jobs.source")
        conn.execute(text("ALTER TABLE scan_jobs ADD COLUMN source TEXT DEFAULT 'manual'"))
    if scan_cols and "mode" not in scan_cols:
        logger.info("migrating schema: add scan_jobs.mode")
        conn.execute(text("ALTER TABLE scan_jobs ADD COLUMN mode TEXT DEFAULT 'incremental'"))

    dl_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(download_records)")).fetchall()}
    if dl_cols and "skipped_files" not in dl_cols:
        logger.info("migrating schema: add download_records.skipped_files")
        conn.execute(text("ALTER TABLE download_records ADD COLUMN skipped_files INTEGER DEFAULT 0"))
    if dl_cols and "target_existed" not in dl_cols:
        logger.info("migrating schema: add download_records.target_existed")
        conn.execute(text("ALTER TABLE download_records ADD COLUMN target_existed INTEGER DEFAULT 0"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """测试时重置连接。"""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
    SessionLocal.configure(bind=None)
