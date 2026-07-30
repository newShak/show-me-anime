"""节点列表排序。"""

from app.constants import ORDER_ASC, ORDER_DESC, SORT_MTIME, SORT_NAME
from app.db.models import Node
from app.utils.natural_sort import natural_sort_key

SORT_FIELDS = {SORT_NAME, SORT_MTIME}
SORT_ORDERS = {ORDER_ASC, ORDER_DESC}


def sort_nodes(nodes: list[Node], sort_by: str, sort_order: str) -> list[Node]:
    """按名称（自然排序）或目录修改时间排序。"""
    reverse = sort_order == ORDER_DESC
    if sort_by == SORT_MTIME:
        return sorted(nodes, key=lambda n: n.dir_mtime or 0, reverse=reverse)
    return sorted(nodes, key=lambda n: natural_sort_key(n.name), reverse=reverse)
