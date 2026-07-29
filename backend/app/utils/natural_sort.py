"""文件名自然排序。"""

import re


def natural_sort_key(name: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def sorted_image_names(filenames: list[str]) -> list[str]:
    return sorted(filenames, key=natural_sort_key)
