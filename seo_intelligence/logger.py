"""
Centralised logging configuration for the SEO Intelligence Platform.

Usage
-----
    from seo_intelligence.logger import get_logger
    log = get_logger(__name__)
    log.info("Starting keyword discovery")
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import LOG_DIR

_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE = LOG_DIR / "seo_platform.log"
_initialized = False


def _setup_root_logger() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler – INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    root.addHandler(ch)

    # Rotating file handler – DEBUG and above (5 MB × 3 backups)
    fh = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    root.addHandler(fh)

    # Silence noisy third-party loggers
    for _noisy in ("urllib3", "httpx", "httpcore", "charset_normalizer"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)


_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (always a child of the configured root)."""
    return logging.getLogger(name)
