"""应用日志配置。"""

import glob
import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOG_FILENAME = "app.log"
_file_handler: logging.Handler | None = None


class SizeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """按天或超过大小滚动，并按保留天数清理旧文件。"""

    def __init__(
        self,
        filename: str,
        *,
        max_bytes: int = 10 * 1024 * 1024,
        retention_days: int = 30,
    ):
        self.max_bytes = max_bytes
        self.retention_days = retention_days
        super().__init__(
            filename,
            when="midnight",
            interval=1,
            backupCount=0,
            encoding="utf-8",
            delay=True,
        )

    def shouldRollover(self, record, msg=None) -> bool:  # noqa: ARG002
        if super().shouldRollover(record):
            return True
        if self.max_bytes > 0 and self.stream:
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() >= self.max_bytes:
                return True
        return False

    def doRollover(self) -> None:
        super().doRollover()
        self._purge_old_files()

    def _purge_old_files(self) -> None:
        if self.retention_days <= 0:
            return
        cutoff = time.time() - self.retention_days * 86400
        pattern = f"{self.baseFilename}*"
        for path in glob.glob(pattern):
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass


def normalize_log_level(level: str | None, default: str = "INFO") -> str:
    """校验并规范化日志级别。"""
    normalized = (level or default).upper()
    return normalized if normalized in VALID_LOG_LEVELS else default


def set_log_level(level: str) -> str:
    """运行时调整根日志级别。"""
    normalized = normalize_log_level(level)
    numeric = getattr(logging, normalized)
    root = logging.getLogger()
    root.setLevel(numeric)
    for handler in root.handlers:
        handler.setLevel(numeric)
    return normalized


def reconfigure_file_logging(
    *,
    log_dir: Path,
    enabled: bool,
    level: str,
    max_bytes: int,
    retention_days: int,
) -> None:
    """按配置挂载或移除文件日志 handler。"""
    global _file_handler
    root = logging.getLogger()
    if _file_handler is not None:
        root.removeHandler(_file_handler)
        _file_handler.close()
        _file_handler = None
    if not enabled:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILENAME
    handler = SizeTimedRotatingFileHandler(
        str(log_path),
        max_bytes=max_bytes,
        retention_days=retention_days,
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    handler.setLevel(getattr(logging, normalize_log_level(level)))
    root.addHandler(handler)
    _file_handler = handler


def setup_logging(level: str | None = None, settings=None) -> str:
    """初始化根日志：stdout + 可选文件滚动日志。"""
    if settings is None:
        from app.config import get_settings

        settings = get_settings()

    log_level = normalize_log_level(level or settings.log_level or os.getenv("LOG_LEVEL"))
    numeric = getattr(logging, log_level)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(numeric)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    stdout_handler.setLevel(numeric)
    root.addHandler(stdout_handler)

    reconfigure_file_logging(
        log_dir=settings.log_dir,
        enabled=settings.log_file_enabled,
        level=log_level,
        max_bytes=settings.log_file_max_bytes,
        retention_days=settings.log_file_retention_days,
    )
    return log_level
