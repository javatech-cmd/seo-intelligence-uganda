"""
Keyword discovery module.

Discovers new keywords via:
    1. Google Suggest (autocomplete) – recursive expansion through the alphabet
    2. Related searches extracted from Google's search page
    3. People Also Ask boxes
    4. Google Trends related queries

All results are deduplicated and persisted to the database.
"""

import re
import time
import random
import urllib.parse
from datetime import date

import requests
from bs4 import BeautifulSoup

from config import (
    ALPHABET,
    EXPAND_ALPHABET,
    GEO,
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    SEED_KEYWORDS,
    USER_AGENTS,
)
from seo_intelligence import cache, database
from seo_intelligence.logger import get_logger
from seo_intelligence.retry import retry

log = get_logger(__name__)

_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
_SEARCH_URL = "https://www.google.com/search"


def _headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-UG,en;q=0.9",
    }


# ── Google Suggest ─────────────────────────────────────────────────────────────

@retry(max_attempts=3, backoff=2.0, exceptions=(requests.RequestException,), on_failure=[])
def _fetch_suggestions(query: str) -> list[str]:
    """Call the Google Suggest JSON endpoint for *query*."""
    cache_key = f"suggest:{GEO}:{query}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "client": "firefox",
        "q": query,
        "gl": GEO,
        "hl": "en",
    }
    resp = requests.get(
        _SUGGEST_URL,
        params=params,
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    raw = resp.json()
    suggestions: list[str] = raw[1] if isinstance(raw, list) and len(raw) > 1 else []
    cache.set(cache_key, suggestions)
    return suggestions


def get_suggestions(keyword: str) -> list[str]:
    """Return Google autocomplete suggestions for *keyword*."""
    time.sleep(RATE_LIMIT_DELAY * random.uniform(0.8, 1.4))
    return _fetch_suggestions(keyword)


def expand_keyword(keyword: str) -> list[str]:
    """
    Expand *keyword* by appending a–z and collecting all suggestions.

    E.g.  "web design" → "web design a" … "web design z"
    """
    found: list[str] = list(get_suggestions(keyword))
    if not EXPAND_ALPHABET:
        return found
    for letter in ALPHABET:
        query = f"{keyword} {letter}"
        found.extend(get_suggestions(query))
        time.sleep(RATE_LIMIT_DELAY * random.uniform(0.5, 1.0))
    return found


# ── Related searches & People Also Ask ────────────────────────────────────────

@retry(max_attempts=3, backoff=2.5, exceptions=(requests.RequestException,), on_failure={})
def _scrape_google_page(keyword: str) -> dict[str, list[str]]:
    """
    Scrape a Google search results page for related searches and PAA questions.

    Returns a dict with keys ``related`` and ``paa``.
    """
    cache_key = f"google_page:{GEO}:{keyword}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "q": keyword,
        "gl": GEO,
        "hl": "en",
        "num": 10,
    }
    resp = requests.get(
        _SEARCH_URL,
        params=params,
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    related: list[str] = []
    paa: list[str] = []

    # Related searches – text inside <a> tags near "People also search for"
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if href.startswith("/search?q=") or href.startswith("/search?as_q="):
            text = tag.get_text(strip=True)
            if text and len(text) > 3:
                related.append(text)

    # People Also Ask – <span> elements with question-like text inside expand blocks
    for span in soup.find_all("span"):
        text = span.get_text(strip=True)
        if text and len(text) > 10 and re.search(r"\b(what|how|why|when|where|can|is|are|do|does)\b", text, re.I):
            if text not in paa:
                paa.append(text)

    result = {"related": related[:20], "paa": paa[:20]}
    cache.set(cache_key, result)
    return result


def get_related_and_paa(keyword: str) -> dict[str, list[str]]:
    """Return related searches and PAA questions for *keyword*."""
    time.sleep(RATE_LIMIT_DELAY * random.uniform(1.0, 2.0))
    return _scrape_google_page(keyword)


# ── Orchestration ─────────────────────────────────────────────────────────────

def discover_keywords(seeds: list[str] | None = None) -> list[str]:
    """
    Run the full keyword discovery pipeline for all seed keywords.

    Steps
    -----
    1. Autocomplete suggestions for each seed.
    2. Alphabet expansion for each seed.
    3. Related searches & PAA for each seed.
    4. Deduplicate and persist to database.

    Returns the sorted list of unique discovered keywords.
    """
    seeds = seeds or SEED_KEYWORDS
    today = date.today().isoformat()
    discovered: set[str] = set(seeds)

    log.info("Starting keyword discovery with %d seeds", len(seeds))

    for seed in seeds:
        log.info("Expanding seed: '%s'", seed)

        # Step 1+2: suggestions + alphabet expansion
        try:
            expanded = expand_keyword(seed)
            for kw in expanded:
                discovered.add(kw.strip().lower())
        except Exception as exc:
            log.warning("Expansion failed for '%s': %s", seed, exc)

        # Step 3: related searches + PAA
        try:
            extras = get_related_and_paa(seed)
            for kw in extras.get("related", []) + extras.get("paa", []):
                discovered.add(kw.strip().lower())
        except Exception as exc:
            log.warning("Related/PAA failed for '%s': %s", seed, exc)

    all_kws = sorted(discovered)
    log.info("Keyword discovery complete: %d unique keywords", len(all_kws))

    # Persist
    for kw in all_kws:
        try:
            database.upsert_keyword(kw, today, source="discovery")
        except Exception as exc:
            log.debug("DB upsert failed for '%s': %s", kw, exc)

    return all_kws
