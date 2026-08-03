"""标签管理辅助。"""

from sqlalchemy.orm import Session

from app.db.models import Tag


def ensure_tags_by_names(db: Session, names: list[str]) -> list[Tag]:
    """按名称获取或创建标签，忽略空白与重复。"""
    tags: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        name = raw.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        tag = db.query(Tag).filter(Tag.name == name).first()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags
