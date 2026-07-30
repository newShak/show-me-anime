"""数据库连接与会话。"""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

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


def _migrate_schema(conn) -> None:
    """轻量 schema 迁移（SQLite 无 Alembic 时使用）。"""
    cols = {row[1] for row in conn.execute(text("PRAGMA table_info(nodes)")).fetchall()}
    if "subdir_count" not in cols:
        conn.execute(text("ALTER TABLE nodes ADD COLUMN subdir_count INTEGER DEFAULT 0"))


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
