"""在画廊根目录下创建文件夹并写入节点索引。"""

import re
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.config import Settings
from app.db.models import Node
from app.services.node_admin import sync_node_search_index
from app.services.scan_runner import run_scan


def _safe_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name.strip())
    cleaned = cleaned.strip(". ")
    return cleaned[:120]


def _resolve_parent_id(db: Session, path: str) -> int | None:
    if "/" not in path:
        return None
    parent_path = path.rsplit("/", 1)[0]
    parent = db.query(Node).filter(Node.path == parent_path).one_or_none()
    return parent.id if parent else None


def _upsert_container_node(db: Session, settings: Settings, rel: str, name: str) -> Node:
    node = db.query(Node).filter(Node.path == rel).one_or_none()
    if node is not None:
        return node
    dest = (settings.gallery_root / rel).resolve()
    mtime = dest.stat().st_mtime
    node = Node(
        name=name,
        path=rel,
        parent_id=_resolve_parent_id(db, rel),
        node_type=constants.CONTAINER,
        source_type=constants.SOURCE_FOLDER,
        image_count=0,
        subdir_count=0,
        archive_count=0,
        cover_rel_path=None,
        dir_mtime=mtime,
        created_at=time.time(),
        updated_at=time.time(),
    )
    db.add(node)
    db.flush()
    sync_node_search_index(db, node)
    db.commit()
    db.refresh(node)
    return node


def mkdir_node(db: Session, settings: Settings, parent_id: int | None, name: str) -> tuple[Node, str]:
    folder = _safe_name(name)
    if not folder:
        raise ValueError("invalid folder name")

    parent_path = ""
    if parent_id is not None:
        parent = db.get(Node, parent_id)
        if parent is None:
            raise ValueError("parent not found")
        if parent.source_type == "zip":
            raise ValueError("cannot mkdir inside archive")
        parent_path = parent.path

    rel = f"{parent_path}/{folder}" if parent_path else folder
    rel = rel.replace("\\", "/")
    dest = (settings.gallery_root / rel).resolve()
    root = settings.gallery_root.resolve()
    if not str(dest).startswith(str(root)):
        raise ValueError("path escapes gallery root")

    if dest.exists():
        if not dest.is_dir():
            raise ValueError("path already exists")
        node = _upsert_container_node(db, settings, rel, folder)
        return node, rel

    dest.mkdir(parents=False, exist_ok=False)
    run_scan(source="mkdir", changed_paths=[rel, parent_path] if parent_path else [rel])
    db.expire_all()
    node = db.query(Node).filter(Node.path == rel).one_or_none()
    if node is None:
        node = _upsert_container_node(db, settings, rel, folder)
    return node, rel
