"""文件名自然排序。"""

import re


def natural_sort_key(name: str) -> list:
    """按数字分段排序。isdigit() 对上标也返回 True，但 int() 只接受十进制数字。"""
    key = []
    for part in re.split(r"(\d+)", name):
        if not part.isdigit():
            key.append(part.lower())
            continue
        try:
            key.append(int(part))
        except ValueError:
            key.append(part.lower())
    return key


def sorted_image_names(filenames: list[str]) -> list[str]:
    return sorted(filenames, key=natural_sort_key)
