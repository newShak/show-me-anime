"""FTS5 搜索索引与查询。"""

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Node


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


def build_fts_query(raw: str) -> str:
    parts = re.findall(r"[\w\-]+", raw, flags=re.UNICODE)
    if not parts:
        return ""
    return " AND ".join(f'"{part}"*' for part in parts)


def search_nodes(db: Session, q: str, limit: int = 20, offset: int = 0) -> tuple[list[Node], int]:
    fts_q = build_fts_query(q)
    if not fts_q:
        return [], 0

    count_row = db.execute(
        text("SELECT COUNT(*) FROM search_index WHERE search_index MATCH :q"),
        {"q": fts_q},
    ).scalar_one()

    rows = db.execute(
        text(
            """
            SELECT node_id FROM search_index
            WHERE search_index MATCH :q
            ORDER BY rank
            LIMIT :limit OFFSET :offset
            """
        ),
        {"q": fts_q, "limit": limit, "offset": offset},
    ).fetchall()

    ids = [row[0] for row in rows]
    if not ids:
        return [], count_row

    nodes = db.query(Node).filter(Node.id.in_(ids)).all()
    order = {node_id: idx for idx, node_id in enumerate(ids)}
    nodes.sort(key=lambda n: order[n.id])
    return nodes, count_row
