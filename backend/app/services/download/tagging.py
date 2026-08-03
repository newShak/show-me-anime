"""外站下载完成后节点打标。"""

import logging

from sqlalchemy.orm import Session

from app.db.models import Node, NodeTag
from app.services.node_admin import sync_node_search_index
from app.services.tag_admin import ensure_tags_by_names

logger = logging.getLogger(__name__)


def resolve_job_tag_ids(db: Session, tag_ids: list[int], import_remote_tags: list[str]) -> list[int]:
    """合并本地 tag id 与待导入的外站 tag 名。"""
    resolved = list(dict.fromkeys(tag_ids))
    if import_remote_tags:
        for tag in ensure_tags_by_names(db, import_remote_tags):
            if tag.id not in resolved:
                resolved.append(tag.id)
    return resolved


def apply_tags_to_node(db: Session, target_rel_path: str, tag_ids: list[int]) -> int:
    """按路径为节点追加标签，返回新增关联数。"""
    if not tag_ids:
        return 0
    node = db.query(Node).filter(Node.path == target_rel_path).one_or_none()
    if node is None:
        logger.warning("apply tags skipped, node not found path=%s", target_rel_path)
        return 0

    existing = {nt.tag_id for nt in db.query(NodeTag).filter(NodeTag.node_id == node.id).all()}
    added = 0
    for tag_id in tag_ids:
        if tag_id in existing:
            continue
        db.add(NodeTag(node_id=node.id, tag_id=tag_id))
        existing.add(tag_id)
        added += 1
    if added:
        sync_node_search_index(db, node)
        db.commit()
        logger.info("apply tags path=%s added=%s tag_ids=%s", target_rel_path, added, tag_ids)
    return added
