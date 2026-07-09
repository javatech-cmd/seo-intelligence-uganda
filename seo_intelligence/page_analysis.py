"""
Page analysis module.

Visits each ranking URL and extracts:
    H1 / H2 / H3 headings, word count, image count, table count,
    FAQ sections, JSON-LD schema, OpenGraph tags, meta description,
    reading time, and a content quality score.
"""

import json
import random
import re
import time
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import RATE_LIMIT_DELAY, REQUEST_TIMEOUT, USER_AGENTS
from seo_intelligence import cache, database
from seo_intelligence.logger import get_logger
from seo_intelligence.retry import retry

log = get_logger(__name__)

_READING_WPM = 238  # average adult reading speed


def _headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-UG,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


@retry(max_attempts=3, backoff=2.5, exceptions=(requests.RequestException,), on_failure=None)
def _fetch_html(url: str) -> str | None:
    resp = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _detect_faqs(soup: BeautifulSoup) -> int:
    """Count FAQ-like blocks (question+answer patterns)."""
    count = 0
    # Look for FAQ schema
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "FAQPage":
                count += len(data.get("mainEntity", []))
        except Exception:
            pass
    # Look for semantic FAQ sections
    for section in soup.find_all(["section", "div"], class_=re.compile(r"faq|accordion", re.I)):
        count += len(section.find_all(["h3", "h4", "dt", "summary"]))
    return count


def _extract_schema_types(soup: BeautifulSoup) -> str:
    """Return comma-separated list of JSON-LD @type values."""
    types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                t = data.get("@type")
                if t:
                    types.append(str(t))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        t = item.get("@type")
                        if t:
                            types.append(str(t))
        except Exception:
            pass
    return ",".join(sorted(set(types)))


def _content_quality_score(
    word_count: int,
    image_count: int,
    table_count: int,
    faq_count: int,
    schema_types: str,
    has_og: bool,
    has_h2: bool,
) -> float:
    """
    Score a page's content quality (0–100).

    Factors
    -------
    word_count  : 40 pts max (1 pt per 50 words, capped at 2000 words)
    images      : 10 pts max
    tables      : 5 pts max
    faqs        : 10 pts max
    schema      : 15 pts if schema present
    og tags     : 10 pts if OG present
    h2 headings : 10 pts if h2 present
    """
    score = 0.0
    score += min(word_count / 50, 40.0)
    score += min(image_count * 2.0, 10.0)
    score += min(table_count * 2.5, 5.0)
    score += min(faq_count * 2.5, 10.0)
    if schema_types:
        score += 15.0
    if has_og:
        score += 10.0
    if has_h2:
        score += 10.0
    return round(min(score, 100.0), 2)


def analyse_page(url: str) -> dict | None:
    """
    Fetch and analyse a single URL.

    Returns a dict of extracted page features or ``None`` on failure.
    """
    cache_key = f"page:{url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = date.today().isoformat()
    html = _fetch_html(url)
    if html is None:
        log.warning("Could not fetch %s", url)
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Remove script / style noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    body_text = soup.get_text(separator=" ", strip=True)

    h1 = (soup.find("h1") or soup.new_tag("span")).get_text(strip=True)[:300]
    h2s = "|".join(t.get_text(strip=True) for t in soup.find_all("h2"))[:1000]
    h3s = "|".join(t.get_text(strip=True) for t in soup.find_all("h3"))[:1000]
    word_count = _count_words(body_text)
    image_count = len(soup.find_all("img"))
    table_count = len(soup.find_all("table"))
    faq_count = _detect_faqs(soup)
    schema_types = _extract_schema_types(soup)

    # Meta description
    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    meta_description = (meta_desc_tag or {}).get("content", "") if meta_desc_tag else ""

    # OpenGraph
    og_title_tag = soup.find("meta", attrs={"property": "og:title"})
    og_title = og_title_tag.get("content", "") if og_title_tag else ""
    has_og = bool(og_title_tag)

    # Last-Modified header (best-effort – we already have the response cached)
    last_modified = ""

    reading_time = round(word_count / _READING_WPM, 2)
    quality = _content_quality_score(
        word_count, image_count, table_count, faq_count,
        schema_types, has_og, bool(h2s),
    )

    result = {
        "url": url,
        "date": today,
        "domain": _extract_domain(url),
        "h1": h1,
        "h2s": h2s,
        "h3s": h3s,
        "word_count": word_count,
        "image_count": image_count,
        "table_count": table_count,
        "faq_count": faq_count,
        "schema_types": schema_types,
        "meta_description": meta_description[:500],
        "og_title": og_title[:300],
        "reading_time_min": reading_time,
        "last_modified": last_modified,
        "content_quality_score": quality,
    }

    cache.set(cache_key, result)
    database.upsert_page_analysis(result)
    return result


def analyse_pages(urls: list[str]) -> list[dict]:
    """
    Analyse a list of URLs sequentially with rate-limiting.

    Returns a list of non-None result dicts.
    """
    results: list[dict] = []
    for url in urls:
        try:
            log.info("Analysing page: %s", url)
            result = analyse_page(url)
            if result:
                results.append(result)
        except Exception as exc:
            log.warning("Page analysis failed for %s: %s", url, exc)
        time.sleep(RATE_LIMIT_DELAY * random.uniform(1.0, 2.0))
    return results
