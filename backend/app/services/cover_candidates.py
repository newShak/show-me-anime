"""容器封面候选与继承路径。"""

from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.db.models import Node
from app.utils.natural_sort import natural_sort_key


def child_cover_path(child: Node) -> str | None:
    """子节点封面相对父容器的路径（与 scanner 继承格式一致）。"""
    if child.source_type == constants.SOURCE_ZIP:
        if not child.cover_rel_path:
            return None
        return f"{Path(child.path).name}::{child.cover_rel_path}"
    if not child.cover_rel_path:
        return None
    return f"{child.name}/{child.cover_rel_path}"


def _children_map(db: Session) -> dict[int | None, list[Node]]:
    children: dict[int | None, list[Node]] = {}
    for node in db.query(Node).all():
        children.setdefault(node.parent_id, []).append(node)
    for items in children.values():
        items.sort(key=lambda n: natural_sort_key(n.name))
    return children


def inherit_container_cover(db: Session, node: Node) -> str | None:
    """纯容器自动继承：第一个有封面的子项。"""
    for child in _children_map(db).get(node.id, []):
        path = child_cover_path(child)
        if path:
            return path
    return None


def _collect_descendant_covers(
    node_id: int,
    children: dict[int | None, list[Node]],
    prefix: str = "",
) -> list[tuple[str, Node]]:
    """递归收集子树内所有可选封面。"""
    results: list[tuple[str, Node]] = []
    for child in children.get(node_id, []):
        if child.node_type == constants.CONTAINER and child.image_count == 0:
            nested_prefix = f"{prefix}{child.name}/" if prefix else f"{child.name}/"
            results.extend(_collect_descendant_covers(child.id, children, nested_prefix))
            continue
        path = child_cover_path(child)
        if not path:
            continue
        value = f"{prefix}{path}" if prefix else path
        results.append((value, child))
    return results


def list_cover_candidates(db: Session, node: Node) -> list[dict]:
    """返回容器/混合节点可选封面列表。"""
    children = _children_map(db)
    items: list[dict] = []

    for value, source in _collect_descendant_covers(node.id, children):
        cover_name = value.split("::")[-1].split("/")[-1]
        label = f"{source.name} · {cover_name}"
        items.append(
            {
                "value": value,
                "label": label,
                "source_node_id": source.id,
            }
        )
    return items


def candidate_values(db: Session, node: Node) -> set[str]:
    """容器可选封面路径集合。"""
    return {item["value"] for item in list_cover_candidates(db, node)}
