"""
Disk-backed cache with TTL support.

Cached responses are stored as JSON files under CACHE_DIR.
The cache key is derived from a SHA-256 hash of the request identifier.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from config import CACHE_DIR, CACHE_TTL_HOURS
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

_TTL_SECONDS = CACHE_TTL_HOURS * 3600


def _key_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def get(key: str) -> Any | None:
    """
    Return cached value for *key* if it exists and has not expired.

    Returns ``None`` on miss or expiry.
    """
    path = _key_path(key)
    if not path.exists():
        return None
    try:
        payload: dict[str, Any] = json.loads(path.read_text("utf-8"))
        if time.time() - payload["ts"] > _TTL_SECONDS:
            path.unlink(missing_ok=True)
            log.debug("Cache expired for key=%s", key[:60])
            return None
        log.debug("Cache hit for key=%s", key[:60])
        return payload["data"]
    except Exception as exc:
        log.warning("Cache read error for key=%s: %s", key[:60], exc)
        path.unlink(missing_ok=True)
        return None


def set(key: str, data: Any) -> None:
    """Persist *data* to the cache under *key*."""
    path = _key_path(key)
    try:
        path.write_text(
            json.dumps({"ts": time.time(), "data": data}, ensure_ascii=False),
            encoding="utf-8",
        )
        log.debug("Cache set for key=%s", key[:60])
    except Exception as exc:
        log.warning("Cache write error for key=%s: %s", key[:60], exc)


def invalidate(key: str) -> None:
    """Remove a cache entry."""
    _key_path(key).unlink(missing_ok=True)


def clear_all() -> None:
    """Delete every cached file."""
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
        removed += 1
    log.info("Cache cleared (%d entries removed)", removed)
