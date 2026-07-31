"""wnacg 首页/分类浏览导航（与站点 nav 结构一致）。"""

from dataclasses import dataclass, field


@dataclass
class BrowseNavItem:
    label: str
    cate_id: int | None = None
    children: list["BrowseNavItem"] = field(default_factory=list)


BROWSE_NAV: list[BrowseNavItem] = [
    BrowseNavItem(label="首頁", cate_id=None),
    BrowseNavItem(
        label="同人誌",
        cate_id=5,
        children=[
            BrowseNavItem(label="漢化", cate_id=1),
            BrowseNavItem(label="日語", cate_id=12),
            BrowseNavItem(label="English", cate_id=16),
            BrowseNavItem(label="CG畫集", cate_id=2),
            BrowseNavItem(label="AI圖集", cate_id=37),
            BrowseNavItem(label="3D漫畫", cate_id=22),
            BrowseNavItem(label="Cosplay", cate_id=3),
        ],
    ),
    BrowseNavItem(
        label="單行本",
        cate_id=6,
        children=[
            BrowseNavItem(label="漢化", cate_id=9),
            BrowseNavItem(label="日語", cate_id=13),
            BrowseNavItem(label="English", cate_id=17),
        ],
    ),
    BrowseNavItem(
        label="雜誌&短篇",
        cate_id=7,
        children=[
            BrowseNavItem(label="漢化", cate_id=10),
            BrowseNavItem(label="日語", cate_id=14),
            BrowseNavItem(label="English", cate_id=18),
        ],
    ),
    BrowseNavItem(
        label="韓漫",
        cate_id=19,
        children=[
            BrowseNavItem(label="漢化", cate_id=20),
            BrowseNavItem(label="其他", cate_id=21),
        ],
    ),
]


def nav_item_by_cate(cate_id: int | None) -> BrowseNavItem | None:
    for item in BROWSE_NAV:
        if item.cate_id == cate_id:
            return item
        for child in item.children:
            if child.cate_id == cate_id:
                return child
    return None


def browse_title(cate_id: int | None) -> str:
    if cate_id is None:
        return "首頁"
    item = nav_item_by_cate(cate_id)
    if not item:
        return f"分類 {cate_id}"
    parent = next((p for p in BROWSE_NAV if any(c.cate_id == cate_id for c in p.children)), None)
    if parent and parent.cate_id != cate_id:
        return f"{parent.label} · {item.label}"
    return item.label
