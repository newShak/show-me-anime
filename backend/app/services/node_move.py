"""节点移动：磁盘目录/压缩包 + 数据库子树路径更新。"""

import logging
import shutil
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node, ScanJob
from app.services.node_admin import sync_node_search_index
from app.services.node_delete import collect_subtree_nodes, filter_deletion_roots, resolve_node_dir
from app.services.scanner import Scanner

logger = logging.getLogger(__name__)


def _resolve_parent_id(db: Session, path_str: str) -> int | None:
    if not path_str:
        return None
    parent_path = str(Path(path_str).parent.as_posix())
    if parent_path == ".":
        parent_path = ""
    if not parent_path:
        return None
    parent = db.query(Node).filter(Node.path == parent_path).first()
    return parent.id if parent else None


def _is_under_path(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _is_valid_target(node: Node) -> bool:
    return node.source_type == constants.SOURCE_FOLDER


def _dest_path(node: Node, target_parent: Node | None) -> str:
    name = Path(node.path).name
    if target_parent is None:
        return name
    return f"{target_parent.path}/{name}"


def _validate_target(db: Session, node: Node, target_parent_id: int | None) -> str | None:
    if target_parent_id == node.parent_id:
        return f"{node.name}: 已在目标位置"

    if target_parent_id == node.id:
        return f"{node.name}: 不能移动到自身"

    target_parent = None
    if target_parent_id is not None:
        target_parent = db.get(Node, target_parent_id)
        if target_parent is None:
            return "目标文件夹不存在"
        if not _is_valid_target(target_parent):
            return "目标必须是文件夹"
        if _is_under_path(target_parent.path, node.path):
            return f"{node.name}: 不能移动到自身或子目录内"

    new_path = _dest_path(node, target_parent)
    conflict = db.query(Node).filter(Node.path == new_path).first()
    if conflict is not None and conflict.id != node.id:
        return f"{node.name}: 目标位置已存在「{conflict.name}」"
    return None


def _refresh_container_covers(db: Session, settings: Settings) -> None:
    job = ScanJob(status=constants.SCAN_DONE, added=0, updated=0, removed=0)
    Scanner(settings)._apply_container_covers(db, job)


def move_node_subtree(
    db: Session,
    node: Node,
    target_parent_id: int | None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    target_parent = db.get(Node, target_parent_id) if target_parent_id is not None else None
    old_path = node.path
    new_path = _dest_path(node, target_parent)
    old_parent_id = node.parent_id

    src = resolve_node_dir(settings.gallery_root, node)
    dst = settings.gallery_root / new_path
    if dst.exists():
        raise ValueError(f"目标路径已存在: {new_path}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    logger.info("moved disk %s -> %s", old_path, new_path)

    subtree = collect_subtree_nodes(db, old_path)
    now = time.time()
    for item in subtree:
        if item.path == old_path:
            item.path = new_path
        else:
            item.path = new_path + item.path[len(old_path) :]
        item.parent_id = _resolve_parent_id(db, item.path)
        item.updated_at = now
        sync_node_search_index(db, item)

    if old_parent_id is not None and node.source_type != constants.SOURCE_ZIP:
        old_parent = db.get(Node, old_parent_id)
        if old_parent is not None:
            old_parent.subdir_count = max(0, old_parent.subdir_count - 1)

    if target_parent_id is not None and node.source_type != constants.SOURCE_ZIP:
        new_parent = db.get(Node, target_parent_id)
        if new_parent is not None:
            new_parent.subdir_count += 1

    _refresh_container_covers(db, settings)


def move_nodes(
    db: Session,
    node_ids: list[int],
    target_parent_id: int | None,
    settings: Settings | None = None,
) -> tuple[int, list[str]]:
    settings = settings or get_settings()
    nodes = [db.get(Node, nid) for nid in node_ids]
    missing = [str(nid) for nid, node in zip(node_ids, nodes, strict=True) if node is None]
    valid = [node for node in nodes if node is not None]
    roots = filter_deletion_roots(valid)

    moved = 0
    errors: list[str] = list(missing)
    logger.info(
        "move nodes requested ids=%s target=%s roots=%s",
        node_ids,
        target_parent_id,
        [node.path for node in roots],
    )

    for node in roots:
        err = _validate_target(db, node, target_parent_id)
        if err:
            errors.append(err)
            continue
        try:
            move_node_subtree(db, node, target_parent_id, settings)
            moved += 1
        except (ValueError, OSError) as exc:
            logger.warning("move failed id=%s path=%s error=%s", node.id, node.path, exc)
            errors.append(f"{node.name}: {exc}")

    db.commit()
    logger.info("move finished moved=%s errors=%s", moved, len(errors))
    return moved, errors
