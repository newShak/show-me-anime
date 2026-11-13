"""节点移动：磁盘重命名 + 子树路径前缀更新。封面交给随后的扫描。"""

import logging
import shutil
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node
from app.services.node_delete import filter_deletion_roots, resolve_node_dir
from app.services.scan_runner import scan_lock, schedule_scan

logger = logging.getLogger(__name__)


def _like_prefix(path: str) -> str:
    escaped = path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}/%"


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


def _retarget_subtree(db: Session, old_path: str, new_path: str, target_parent_id: int | None) -> None:
    """一次改写子树 path 和搜索索引。只改被移动根节点的 parent_id，子孙关系不变。"""
    params = {
        "new_path": new_path,
        "cut": len(old_path) + 1,
        "now": time.time(),
        "old_path": old_path,
        "like": _like_prefix(old_path),
        "parent_id": target_parent_id,
    }
    where = "path = :old_path OR path LIKE :like ESCAPE '\\'"
    db.execute(
        text(
            f"""
            UPDATE nodes
            SET path = :new_path || substr(path, :cut),
                parent_id = CASE WHEN path = :old_path THEN :parent_id ELSE parent_id END,
                updated_at = :now
            WHERE {where}
            """
        ),
        params,
    )
    db.execute(
        text(
            f"""
            UPDATE search_index
            SET path = :new_path || substr(path, :cut)
            WHERE {where}
            """
        ),
        params,
    )


def _adjust_parent_counts(
    db: Session,
    old_parent_id: int | None,
    target_parent_id: int | None,
    source_type: str,
) -> None:
    field = "archive_count" if source_type == constants.SOURCE_ZIP else "subdir_count"

    def bump(parent_id: int | None, delta: int) -> None:
        if parent_id is None:
            return
        parent = db.get(Node, parent_id)
        if parent is None:
            return
        setattr(parent, field, max(0, getattr(parent, field) + delta))

    bump(old_parent_id, -1)
    bump(target_parent_id, 1)


def move_node_subtree(
    db: Session,
    node: Node,
    target_parent_id: int | None,
    settings: Settings | None = None,
) -> str:
    """把节点目录重命名到目标下，并改写子树路径。返回新路径。"""
    settings = settings or get_settings()
    target_parent = db.get(Node, target_parent_id) if target_parent_id is not None else None
    old_path = node.path
    new_path = _dest_path(node, target_parent)
    old_parent_id = node.parent_id
    source_type = node.source_type

    src = resolve_node_dir(settings.gallery_root, node)
    dst = settings.gallery_root / new_path
    if dst.exists():
        raise ValueError(f"目标路径已存在: {new_path}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    logger.info("moved disk %s -> %s", old_path, new_path)

    _retarget_subtree(db, old_path, new_path, target_parent_id)
    _adjust_parent_counts(db, old_parent_id, target_parent_id, source_type)
    db.flush()
    # 丢掉内存里的旧 path，避免后续 flush 把前缀更新盖回去
    db.expire_all()
    return new_path


def move_nodes(
    db: Session,
    node_ids: list[int],
    target_parent_id: int | None,
    settings: Settings | None = None,
) -> tuple[int, list[str]]:
    """批量移动。请求内只做重命名和路径更新，封面由随后的扫描补齐。"""
    settings = settings or get_settings()
    changed: list[str] = []
    with scan_lock():
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
            old_path = node.path
            try:
                new_path = move_node_subtree(db, node, target_parent_id, settings)
                changed.extend((old_path, new_path))
                moved += 1
            except (ValueError, OSError) as exc:
                logger.warning("move failed id=%s path=%s error=%s", node.id, old_path, exc)
                errors.append(f"{node.name}: {exc}")

        db.commit()

    if changed and settings.watch_enabled:
        schedule_scan("move", changed)
    logger.info("move finished moved=%s errors=%s", moved, len(errors))
    return moved, errors
