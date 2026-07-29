"""FTS5 搜索索引同步。"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def sync_node_search(db: Session, node_id: int, title: str, path: str, tags: str = "") -> None:
    db.execute(text("DELETE FROM search_index WHERE node_id = :node_id"), {"node_id": node_id})
    db.execute(
        text(
            "INSERT INTO search_index (node_id, title, path, tags) "
            "VALUES (:node_id, :title, :path, :tags)"
        ),
        {"node_id": node_id, "title": title, "path": path, "tags": tags},
    )


def remove_node_search(db: Session, node_id: int) -> None:
    db.execute(text("DELETE FROM search_index WHERE node_id = :node_id"), {"node_id": node_id})
