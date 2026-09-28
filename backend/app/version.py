"""应用版本号（与仓库根目录 VERSION 同步）。"""

from pathlib import Path

_ROOT_VERSION = Path(__file__).resolve().parents[2] / "VERSION"


def read_app_version() -> str:
    try:
        line = _ROOT_VERSION.read_text(encoding="utf-8").splitlines()[0].strip()
    except OSError:
        return "0.0.0-dev"
    return line or "0.0.0-dev"
