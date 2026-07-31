"""wnacg 列表页分类/语言标签（来自 pic_box cate-* CSS）。"""

# 与 /themes/weitu/images/style.css 中 ::before content 一致
CATE_LABELS: dict[int, str] = {
    1: "同人誌漢化",
    2: "同人誌CG畫集",
    3: "寫真 & Cosplay",
    5: "同人誌",
    6: "單行本",
    7: "雜誌&短篇",
    9: "單行本漢化",
    10: "雜誌&短篇漢化",
    12: "同人誌日語",
    13: "單行本日語",
    14: "雜誌&短篇日語",
    16: "同人誌English",
    17: "單行本English",
    18: "雜誌&短篇English",
    19: "韓漫",
    20: "韓漫漢化",
    21: "韓漫日語",
    22: "3D&漫畫",
    23: "3D&漫畫漢化",
    24: "3D&漫畫日語",
    37: "AI&圖集",
}

_LANG_SUFFIXES = ("漢化", "日語", "English", "生肉")


def parse_cate_id(block: str) -> int | None:
    import re

    m = re.search(r'pic_box cate-(\d+)', block, re.I)
    return int(m.group(1)) if m else None


def cate_info(cate_id: int | None) -> tuple[str | None, str | None]:
    """返回 (分类, 语言)。"""
    if cate_id is None:
        return None, None
    label = CATE_LABELS.get(cate_id)
    if not label:
        return None, None
    for suffix in _LANG_SUFFIXES:
        if label.endswith(suffix) and len(label) > len(suffix):
            return label[: -len(suffix)], suffix
    return label, None


def badge_text(category: str | None, language: str | None) -> str | None:
    if category and language:
        return f"{category} / {language}"
    return language or category


def infer_language_from_title(title: str) -> str | None:
    import re

    t = re.sub(r"<[^>]+>", "", title)
    if re.search(r"中国翻訳|中國翻訳|漢化|\[CN\]", t, re.I):
        return "漢化"
    if re.search(r"日語|日本語|生肉", t):
        return "日語" if "日語" in t or "日本語" in t else "生肉"
    if re.search(r"English", t, re.I):
        return "English"
    return None
