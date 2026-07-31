"""节点删除：磁盘目录 + 数据库子树。"""

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node, NodeTag, ReadProgress, RecentView, Favorite
from app.services.search import remove_node_search

logger = logging.getLogger(__name__)


def filter_deletion_roots(nodes: list[Node]) -> list[Node]:
    """若同时选中父/子节点，只保留父节点。"""
    paths = {n.path for n in nodes}
    return [n for n in nodes if not any(p != n.path and n.path.startswith(f"{p}/") for p in paths)]


def resolve_node_dir(gallery_root: Path, node: Node) -> Path:
    if not node.path:
        raise ValueError("不能删除画廊根目录")
    root = gallery_root.resolve()
    target = (gallery_root / node.path).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"非法路径: {node.path}")
    if node.source_type == constants.SOURCE_ZIP:
        if not target.is_file():
            raise ValueError(f"压缩包不存在: {node.path}")
        return target
    if not target.is_dir():
        raise ValueError(f"目录不存在: {node.path}")
    return target


def collect_subtree_nodes(db: Session, path: str) -> list[Node]:
    all_nodes = db.query(Node).all()
    return [n for n in all_nodes if n.path == path or n.path.startswith(f"{path}/")]


def purge_nodes_index(db: Session, nodes: list[Node]) -> int:
    """仅从数据库移除节点索引（不删磁盘），子节点先于父节点，并清理关联表。"""
    if not nodes:
        return 0
    ordered = sorted(nodes, key=lambda n: n.path.count("/"), reverse=True)
    ids = [n.id for n in ordered]
    db.query(NodeTag).filter(NodeTag.node_id.in_(ids)).delete(synchronize_session=False)
    db.query(ReadProgress).filter(ReadProgress.node_id.in_(ids)).delete(synchronize_session=False)
    db.query(RecentView).filter(RecentView.node_id.in_(ids)).delete(synchronize_session=False)
    db.query(Favorite).filter(Favorite.node_id.in_(ids)).delete(synchronize_session=False)
    for node in ordered:
        remove_node_search(db, node.id)
        db.delete(node)
    return len(ordered)


def delete_node_subtree(db: Session, node: Node, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    target = resolve_node_dir(settings.gallery_root, node)
    targets = collect_subtree_nodes(db, node.path)
    logger.info(
        "deleting node id=%s path=%s type=%s subtree=%s",
        node.id,
        node.path,
        node.source_type,
        len(targets),
    )

    if node.source_type == constants.SOURCE_ZIP:
        target.unlink()
    else:
        shutil.rmtree(target)

    if targets:
        purge_nodes_index(db, targets)

    parent_id = node.parent_id
    db.flush()
    if parent_id is not None:
        parent = db.get(Node, parent_id)
        if parent is not None:
            if node.source_type == constants.SOURCE_ZIP:
                parent.archive_count = max(0, parent.archive_count - 1)
            else:
                parent.subdir_count = max(0, parent.subdir_count - 1)
    return len(targets)


def delete_nodes(db: Session, node_ids: list[int], settings: Settings | None = None) -> tuple[int, list[str]]:
    settings = settings or get_settings()
    nodes = [db.get(Node, nid) for nid in node_ids]
    missing = [str(nid) for nid, n in zip(node_ids, nodes, strict=True) if n is None]
    valid = [n for n in nodes if n is not None]
    roots = filter_deletion_roots(valid)

    deleted = 0
    errors: list[str] = list(missing)
    logger.info("delete nodes requested ids=%s roots=%s", node_ids, [n.path for n in roots])
    for node in roots:
        try:
            deleted += delete_node_subtree(db, node, settings)
        except (ValueError, OSError) as exc:
            logger.warning("delete failed id=%s path=%s error=%s", node.id, node.path, exc)
            errors.append(f"{node.name}: {exc}")

    db.commit()
    logger.info("delete finished deleted=%s errors=%s", deleted, len(errors))
    return deleted, errors
