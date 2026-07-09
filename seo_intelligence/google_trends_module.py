"""
Google Trends integration using pytrends.

Fetches interest-over-time and related queries for a list of keywords,
restricted to Uganda (geo="UG").
"""

import time
import random
from datetime import date
from typing import Any

from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError

from config import GEO, TRENDS_TIMEFRAME, RATE_LIMIT_DELAY
from seo_intelligence import cache, database
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

_BATCH_SIZE = 5  # pytrends max keywords per request


def _build_client() -> TrendReq:
    return TrendReq(hl="en-UG", tz=180, timeout=(10, 25), retries=2, backoff_factor=0.5)


def _safe_sleep(base: float = RATE_LIMIT_DELAY) -> None:
    time.sleep(base * random.uniform(1.0, 2.5))


def fetch_trends(keywords: list[str]) -> dict[str, float]:
    """
    Return a mapping of keyword → average interest score (0–100) over the
    configured timeframe for Uganda.

    Processes keywords in batches of 5 to comply with pytrends limits.
    Results are cached for CACHE_TTL_HOURS.
    """
    results: dict[str, float] = {}
    today = date.today().isoformat()

    batches = [keywords[i : i + _BATCH_SIZE] for i in range(0, len(keywords), _BATCH_SIZE)]
    log.info("Fetching Google Trends for %d keywords in %d batches", len(keywords), len(batches))

    for batch in batches:
        cache_key = f"trends:{GEO}:{','.join(sorted(batch))}"
        cached = cache.get(cache_key)
        if cached:
            results.update(cached)
            continue

        try:
            pt = _build_client()
            pt.build_payload(batch, cat=0, timeframe=TRENDS_TIMEFRAME, geo=GEO)
            df = pt.interest_over_time()
            batch_scores: dict[str, float] = {}
            if df is not None and not df.empty:
                for kw in batch:
                    if kw in df.columns:
                        batch_scores[kw] = float(df[kw].mean())
                    else:
                        batch_scores[kw] = 0.0
            else:
                batch_scores = {kw: 0.0 for kw in batch}

            cache.set(cache_key, batch_scores)
            results.update(batch_scores)

            # Also pull related queries for additional keyword discovery
            try:
                related = pt.related_queries()
                for kw in batch:
                    kw_related = related.get(kw, {})
                    for frame_key in ("top", "rising"):
                        frame_df = kw_related.get(frame_key)
                        if frame_df is not None and not frame_df.empty:
                            for rel_kw in frame_df["query"].tolist():
                                database.upsert_keyword(
                                    rel_kw.strip().lower(),
                                    today,
                                    source=f"trends_{frame_key}",
                                )
            except Exception as exc:
                log.debug("Related queries skipped: %s", exc)

        except TooManyRequestsError:
            log.warning("Google Trends rate limit hit – sleeping 60 s")
            time.sleep(60)
        except Exception as exc:
            log.warning("Trends fetch failed for batch %s: %s", batch, exc)
            for kw in batch:
                results.setdefault(kw, 0.0)

        _safe_sleep()

    return results


def update_trend_scores(keywords: list[str]) -> None:
    """Fetch trend scores and update the database for all *keywords*."""
    today = date.today().isoformat()
    scores = fetch_trends(keywords)
    for kw, score in scores.items():
        try:
            database.upsert_keyword(kw, today, trend_score=score, source="google_trends")
        except Exception as exc:
            log.debug("DB update failed for '%s': %s", kw, exc)
    log.info("Trend scores updated for %d keywords", len(scores))
