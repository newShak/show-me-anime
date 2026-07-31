"""读取应用日志文件（供 API / 网页查看）。"""

from __future__ import annotations

from pathlib import Path

LOG_FILENAME = "app.log"


def resolve_log_file(log_dir: Path, name: str | None = None) -> Path:
    """解析并校验日志文件名，防止路径穿越。"""
    safe = (name or LOG_FILENAME).strip()
    if not safe or safe != Path(safe).name or ".." in safe:
        raise ValueError("invalid log file name")
    root = log_dir.resolve()
    path = (root / safe).resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("invalid log file path")
    return path


def list_log_files(log_dir: Path) -> list[dict]:
    """列出日志目录下的 app.log 及滚动文件。"""
    if not log_dir.is_dir():
        return []
    rows: list[dict] = []
    for path in sorted(log_dir.glob(f"{LOG_FILENAME}*"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        rows.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified_at": stat.st_mtime,
            }
        )
    return rows


def _read_last_lines(path: Path, max_lines: int) -> str:
    if max_lines <= 0 or not path.is_file():
        return ""
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size == 0:
            return ""
        block = 8192
        data = b""
        pos = size
        while pos > 0 and data.count(b"\n") <= max_lines:
            step = min(block, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return "".join(lines)


def read_log_content(path: Path, *, tail_lines: int = 500, offset: int = 0) -> dict:
    """读取日志：offset=0 返回尾部 N 行；否则返回 offset 之后的新增内容。"""
    if not path.is_file():
        return {"content": "", "offset": 0, "reset": True, "append": False}

    size = path.stat().st_size
    if offset > size:
        content = _read_last_lines(path, tail_lines)
        return {"content": content, "offset": size, "reset": True, "append": False}

    if offset <= 0:
        content = _read_last_lines(path, tail_lines)
        return {"content": content, "offset": size, "reset": False, "append": False}

    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        content = f.read()
    return {"content": content, "offset": size, "reset": False, "append": True}
