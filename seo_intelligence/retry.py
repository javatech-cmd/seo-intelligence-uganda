"""
Retry decorator with exponential back-off and configurable exceptions.

Usage
-----
    from seo_intelligence.retry import retry

    @retry(max_attempts=3, backoff=2.0, exceptions=(requests.RequestException,))
    def fetch(url: str) -> str:
        ...
"""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from seo_intelligence.logger import get_logger

log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_failure: Any = None,
) -> Callable[[F], F]:
    """
    Decorator that retries *func* up to *max_attempts* times on *exceptions*.

    Parameters
    ----------
    max_attempts:
        Total number of attempts (including the first).
    backoff:
        Multiplicative back-off factor (seconds doubled each retry).
    exceptions:
        Tuple of exception types that trigger a retry.
    on_failure:
        Value to return when all attempts are exhausted (default ``None``).
        If set to ``raise``, re-raises the last exception instead.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = 1.0
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        log.warning(
                            "%s failed (attempt %d/%d): %s – retrying in %.1fs",
                            func.__qualname__,
                            attempt,
                            max_attempts,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        log.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__,
                            max_attempts,
                            exc,
                        )
            if on_failure == "raise" and last_exc is not None:
                raise last_exc
            return on_failure

        return wrapper  # type: ignore[return-value]

    return decorator
