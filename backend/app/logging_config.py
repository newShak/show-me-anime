"""应用日志配置。"""

import logging
import os
import sys

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


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


def setup_logging(level: str | None = None) -> str:
    """初始化根日志；级别由参数、settings 或环境变量 LOG_LEVEL 控制（默认 INFO）。"""
    log_level = normalize_log_level(level or os.getenv("LOG_LEVEL"))
    numeric = getattr(logging, log_level)
    logging.basicConfig(
        level=numeric,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )
    return log_level
