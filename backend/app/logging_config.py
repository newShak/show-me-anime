"""应用日志配置。"""

import logging
import os
import sys

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: str | None = None) -> None:
    """初始化根日志；级别由参数或环境变量 LOG_LEVEL 控制（默认 INFO）。"""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(
        level=numeric,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )
