"""搜索索引与查询（名称/路径/标签包含匹配）。"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Node, NodeTag


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


def extract_search_terms(raw: str) -> list[str]:
    """按空格拆分关键词，每个词在 title/path/tags 中任意包含即算命中（多词 AND）。"""
    return [part for part in raw.strip().split() if part]


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _build_contains_where(terms: list[str]) -> tuple[str, dict[str, str]]:
    clauses: list[str] = []
    params: dict[str, str] = {}
    for i, term in enumerate(terms):
        key = f"t{i}"
        params[key] = _like_pattern(term)
        clauses.append(
            f"(title LIKE :{key} ESCAPE '\\' OR path LIKE :{key} ESCAPE '\\' "
            f"OR tags LIKE :{key} ESCAPE '\\')"
        )
    return " AND ".join(clauses), params


def search_nodes(db: Session, q: str, limit: int = 20, offset: int = 0) -> tuple[list[Node], int]:
    terms = extract_search_terms(q)
    if not terms:
        return [], 0

    where, params = _build_contains_where(terms)
    query_params = {**params, "limit": limit, "offset": offset}

    count_row = db.execute(
        text(f"SELECT COUNT(*) FROM search_index WHERE {where}"),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT node_id FROM search_index
            WHERE {where}
            ORDER BY CASE WHEN title LIKE :t0 ESCAPE '\\' THEN 0 ELSE 1 END, title
            LIMIT :limit OFFSET :offset
            """
        ),
        query_params,
    ).fetchall()

    ids = [row[0] for row in rows]
    if not ids:
        return [], count_row

    nodes = db.query(Node).filter(Node.id.in_(ids)).all()
    order = {node_id: idx for idx, node_id in enumerate(ids)}
    nodes.sort(key=lambda n: order[n.id])
    return nodes, count_row


def _text_match_ids(db: Session, q: str) -> set[int]:
    terms = extract_search_terms(q)
    if not terms:
        return set()
    where, params = _build_contains_where(terms)
    rows = db.execute(text(f"SELECT node_id FROM search_index WHERE {where}"), params).fetchall()
    return {row[0] for row in rows}


def _tag_match_ids(db: Session, tag_ids: list[int]) -> set[int]:
    if not tag_ids:
        return set()
    rows = (
        db.query(NodeTag.node_id)
        .filter(NodeTag.tag_id.in_(tag_ids))
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def search_nodes_by_tags(db: Session, tag_ids: list[int], limit: int = 20, offset: int = 0) -> tuple[list[Node], int]:
    """按标签搜索，多个标签为 OR 关系。"""
    ids = _tag_match_ids(db, tag_ids)
    if not ids:
        return [], 0
    total = len(ids)
    nodes = (
        db.query(Node)
        .filter(Node.id.in_(ids))
        .order_by(Node.name)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return nodes, total


def search_nodes_filtered(
    db: Session,
    q: str | None = None,
    tag_ids: list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Node], int]:
    """关键词与标签组合搜索；同时存在时为 AND，标签之间为 OR。"""
    ids: set[int] | None = None
    if q and q.strip():
        text_ids = _text_match_ids(db, q.strip())
        ids = text_ids
    if tag_ids:
        tag_node_ids = _tag_match_ids(db, tag_ids)
        ids = tag_node_ids if ids is None else ids & tag_node_ids
    if ids is None:
        return [], 0

    ordered = db.query(Node).filter(Node.id.in_(ids)).order_by(Node.name).all()
    total = len(ordered)
    page = ordered[offset : offset + limit]
    return page, total
