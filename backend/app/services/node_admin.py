"""节点管理辅助。"""

from sqlalchemy.orm import Session

from app.db.models import Node, NodeTag, Tag
from app.services.search import sync_node_search


def node_tags_text(db: Session, node_id: int) -> str:
    names = (
        db.query(Tag.name)
        .join(NodeTag, NodeTag.tag_id == Tag.id)
        .filter(NodeTag.node_id == node_id)
        .all()
    )
    return " ".join(name for (name,) in names)


def sync_node_search_index(db: Session, node: Node) -> None:
    sync_node_search(db, node.id, node.name, node.path, node_tags_text(db, node.id))
