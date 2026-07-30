"""SQLAlchemy 模型。"""

import time

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    node_type: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="folder")
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    subdir_count: Mapped[int] = mapped_column(Integer, default=0)
    cover_rel_path: Mapped[str | None] = mapped_column(String, nullable=True)
    dir_mtime: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=lambda: time.time())
    updated_at: Mapped[float] = mapped_column(Float, default=lambda: time.time())

    parent: Mapped["Node | None"] = relationship(remote_side=[id])


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class NodeTag(Base):
    __tablename__ = "node_tags"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class ReadProgress(Base):
    __tablename__ = "read_progress"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), primary_key=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, default=lambda: time.time())


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    added: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    removed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
