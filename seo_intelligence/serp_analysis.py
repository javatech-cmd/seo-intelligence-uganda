"""
SERP analysis module.

Retrieves the first page of Google results for a keyword using:
    1. Google Custom Search JSON API (preferred – requires GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID)
    2. DataForSEO SERP API (premium fallback – requires credentials)
    3. Direct HTML scraping (last resort, rate-limited)

All results are stored in the database.
"""

import random
import time
import urllib.parse
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    GEO,
    GOOGLE_CSE_API_KEY,
    GOOGLE_CSE_ID,
    DATAFORSEO_LOGIN,
    DATAFORSEO_PASSWORD,
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    SERP_RESULTS_PER_PAGE,
    USER_AGENTS,
)
from seo_intelligence import cache, database
from seo_intelligence.logger import get_logger
from seo_intelligence.retry import retry

log = get_logger(__name__)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-UG,en;q=0.9",
    }


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


# ── Google Custom Search API ───────────────────────────────────────────────────

@retry(max_attempts=3, backoff=2.0, exceptions=(requests.RequestException,), on_failure=[])
def _serp_via_cse(keyword: str) -> list[dict]:
    """Fetch SERP data via Google Custom Search JSON API."""
    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_ID:
        return []

    cache_key = f"cse:{GEO}:{keyword}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": keyword,
        "gl": GEO,
        "hl": "en",
        "num": min(SERP_RESULTS_PER_PAGE, 10),
    }
    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    results = [
        {
            "position": idx + 1,
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "domain": _extract_domain(item.get("link", "")),
            "snippet": item.get("snippet", ""),
        }
        for idx, item in enumerate(items)
    ]
    cache.set(cache_key, results)
    return results


# ── DataForSEO ─────────────────────────────────────────────────────────────────

@retry(max_attempts=2, backoff=3.0, exceptions=(requests.RequestException,), on_failure=[])
def _serp_via_dataforseo(keyword: str) -> list[dict]:
    """Fetch SERP data via the DataForSEO SERP API (synchronous endpoint)."""
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        return []

    cache_key = f"dataforseo:{GEO}:{keyword}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    payload = [
        {
            "keyword": keyword,
            "location_code": 2800,  # Uganda
            "language_code": "en",
            "depth": SERP_RESULTS_PER_PAGE,
        }
    ]
    resp = requests.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        json=payload,
        auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []
    try:
        tasks = data.get("tasks", [])
        if tasks and tasks[0].get("status_code") == 20000:
            items = (
                tasks[0].get("result", [{}])[0]
                .get("items", [])
            )
            for item in items:
                if item.get("type") == "organic":
                    results.append(
                        {
                            "position": item.get("rank_absolute", 0),
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "domain": _extract_domain(item.get("url", "")),
                            "snippet": item.get("description", ""),
                        }
                    )
    except Exception as exc:
        log.warning("DataForSEO parse error: %s", exc)

    cache.set(cache_key, results)
    return results


# ── HTML scraping fallback ─────────────────────────────────────────────────────

@retry(max_attempts=3, backoff=3.0, exceptions=(requests.RequestException,), on_failure=[])
def _serp_via_scraping(keyword: str) -> list[dict]:
    """Scrape Google organic results directly (last resort)."""
    cache_key = f"scrape_serp:{GEO}:{keyword}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "q": keyword,
        "gl": GEO,
        "hl": "en",
        "num": SERP_RESULTS_PER_PAGE,
    }
    resp = requests.get(
        "https://www.google.com/search",
        params=params,
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results: list[dict] = []
    position = 1
    for div in soup.select("div.g, div[data-hveid]"):
        a_tag = div.find("a", href=True)
        h3_tag = div.find("h3")
        snippet_tag = div.find("span", class_=lambda c: c and "st" in c)
        if not a_tag or not h3_tag:
            continue
        url = a_tag["href"]
        if not url.startswith("http"):
            continue
        results.append(
            {
                "position": position,
                "title": h3_tag.get_text(strip=True),
                "url": url,
                "domain": _extract_domain(url),
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
            }
        )
        position += 1
        if position > SERP_RESULTS_PER_PAGE:
            break

    cache.set(cache_key, results)
    return results


# ── Public interface ───────────────────────────────────────────────────────────

def fetch_serp(keyword: str) -> list[dict]:
    """
    Return SERP results for *keyword* using the best available method.

    Priority: CSE API → DataForSEO → HTML scraping.
    Each result dict has: position, title, url, domain, snippet.
    """
    results = _serp_via_cse(keyword)
    if not results:
        results = _serp_via_dataforseo(keyword)
    if not results:
        log.info("Falling back to HTML scraping for '%s'", keyword)
        time.sleep(RATE_LIMIT_DELAY * random.uniform(2.0, 4.0))
        results = _serp_via_scraping(keyword)
    return results


def analyse_serp(keywords: list[str]) -> dict[str, list[dict]]:
    """
    Run SERP analysis for all *keywords*.

    Persists each result to the database and returns a mapping of
    keyword → list of SERP result dicts.
    """
    today = date.today().isoformat()
    all_results: dict[str, list[dict]] = {}

    for kw in keywords:
        log.info("SERP analysis: '%s'", kw)
        try:
            results = fetch_serp(kw)
            all_results[kw] = results
            for r in results:
                database.upsert_serp_result(
                    keyword=kw,
                    today=today,
                    position=r["position"],
                    title=r["title"],
                    url=r["url"],
                    domain=r["domain"],
                    snippet=r["snippet"],
                )
        except Exception as exc:
            log.warning("SERP failed for '%s': %s", kw, exc)
            all_results[kw] = []

        time.sleep(RATE_LIMIT_DELAY * random.uniform(1.0, 2.5))

    log.info("SERP analysis complete for %d keywords", len(keywords))
    return all_results


def compute_serp_weakness(serp_results: list[dict], page_analyses: list[dict]) -> float:
    """
    Compute a SERP weakness score (0–1) for a keyword based on its ranking pages.

    Higher = weaker competition = better opportunity.
    Factors: low average word count, few images, missing schema, few FAQs.
    """
    if not page_analyses:
        return 0.5  # neutral when no data

    avg_words = sum(p.get("word_count", 0) for p in page_analyses) / len(page_analyses)
    avg_images = sum(p.get("image_count", 0) for p in page_analyses) / len(page_analyses)
    schema_coverage = sum(1 for p in page_analyses if p.get("schema_types")) / len(page_analyses)
    faq_coverage = sum(1 for p in page_analyses if p.get("faq_count", 0) > 0) / len(page_analyses)

    # Lower content quality → higher weakness score
    word_score = max(0.0, 1.0 - avg_words / 3000)
    image_score = max(0.0, 1.0 - avg_images / 10)
    schema_score = 1.0 - schema_coverage
    faq_score = 1.0 - faq_coverage

    weakness = (word_score * 0.35 + image_score * 0.20 + schema_score * 0.25 + faq_score * 0.20)
    return round(min(max(weakness, 0.0), 1.0), 4)
