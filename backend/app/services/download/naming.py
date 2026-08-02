"""下载目标文件夹命名。"""

import html
import re

_HTML = re.compile(r"<[^>]+>")
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_LEN = 60


def album_folder_name(title: str, album_id: str) -> str:
    text = _HTML.sub("", title)
    text = html.unescape(text).strip()
    text = _INVALID.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    slug = text.replace(" ", "-")
    if len(slug) > _MAX_LEN:
        slug = slug[:_MAX_LEN].rstrip("-")
    if not slug or slug == album_id:
        return f"album-{album_id}"
    if slug.isdigit():
        return f"{slug}-{album_id}"
    return slug
