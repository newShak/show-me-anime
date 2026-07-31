"""最近浏览与收藏业务逻辑。"""

import time

from sqlalchemy.orm import Session

from app.db.models import Favorite, Node, RecentView


def touch_recent_view(db: Session, node_id: int) -> None:
    row = db.get(RecentView, node_id)
    now = time.time()
    if row:
        row.viewed_at = now
    else:
        db.add(RecentView(node_id=node_id, viewed_at=now))


def trim_recent_views(db: Session, limit: int) -> None:
    if limit < 1:
        return
    rows = db.query(RecentView.node_id).order_by(RecentView.viewed_at.desc()).all()
    if len(rows) <= limit:
        return
    stale = [row[0] for row in rows[limit:]]
    db.query(RecentView).filter(RecentView.node_id.in_(stale)).delete(synchronize_session=False)


def list_recent_nodes(db: Session, limit: int) -> list[Node]:
    rows = (
        db.query(RecentView, Node)
        .join(Node, Node.id == RecentView.node_id)
        .order_by(RecentView.viewed_at.desc())
        .limit(limit)
        .all()
    )
    return [node for _, node in rows]


def clear_recent_views(db: Session) -> None:
    db.query(RecentView).delete(synchronize_session=False)


def toggle_favorite(db: Session, node_id: int) -> bool:
    row = db.get(Favorite, node_id)
    if row:
        db.delete(row)
        return False
    db.add(Favorite(node_id=node_id, created_at=time.time()))
    return True


def list_favorite_ids(db: Session) -> list[int]:
    rows = db.query(Favorite.node_id).order_by(Favorite.created_at.desc()).all()
    return [row[0] for row in rows]


def list_favorite_nodes(db: Session, offset: int = 0, limit: int = 20) -> tuple[list[Node], int]:
    total = db.query(Favorite).count()
    if total == 0:
        return [], 0
    rows = (
        db.query(Favorite, Node)
        .join(Node, Node.id == Favorite.node_id)
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [node for _, node in rows], total


def clear_favorites(db: Session) -> None:
    db.query(Favorite).delete(synchronize_session=False)
