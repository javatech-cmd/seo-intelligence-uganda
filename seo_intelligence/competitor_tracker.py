"""
Competitor tracking module.

Identifies and tracks competitor domains across all crawled SERP results.
Metrics tracked per competitor per day:
    - keyword_count      : number of unique keywords where the domain ranks
    - visibility_score   : weighted sum of (11 - position) for top-10 rankings
    - ranking changes    : deltas compared to the previous recorded day
"""

from datetime import date

from config import KNOWN_COMPETITORS
from seo_intelligence import database
from seo_intelligence.logger import get_logger

log = get_logger(__name__)


def _compute_visibility(positions: list[int]) -> float:
    """
    Estimate visibility as the sum of (11 - position) for top-10 positions.

    A #1 ranking contributes 10 points, #10 contributes 1 point.
    """
    return sum(max(0, 11 - p) for p in positions if 1 <= p <= 10)


def discover_competitors_from_serps(serp_data: dict[str, list[dict]]) -> set[str]:
    """
    Walk all SERP results and collect every unique domain.

    Returns the full set of discovered domain strings.
    """
    discovered: set[str] = set(KNOWN_COMPETITORS)
    for kw_results in serp_data.values():
        for result in kw_results:
            domain = result.get("domain", "").strip().lower()
            if domain:
                discovered.add(domain)
    log.info("Discovered %d unique competitor domains", len(discovered))
    return discovered


def track_competitors(serp_data: dict[str, list[dict]]) -> dict[str, dict]:
    """
    Compute per-domain stats from *serp_data* and persist to the database.

    Parameters
    ----------
    serp_data:
        Mapping of keyword → list of SERP result dicts (from serp_analysis).

    Returns
    -------
    dict mapping domain → {keyword_count, visibility_score, keywords: list[str]}
    """
    today = date.today().isoformat()

    # Aggregate per-domain stats
    domain_stats: dict[str, dict] = {}
    for keyword, results in serp_data.items():
        for result in results:
            domain = result.get("domain", "").strip().lower()
            position = result.get("position", 99)
            if not domain:
                continue
            if domain not in domain_stats:
                domain_stats[domain] = {"keywords": [], "positions": []}
            domain_stats[domain]["keywords"].append(keyword)
            domain_stats[domain]["positions"].append(position)

    # Persist and return
    summary: dict[str, dict] = {}
    for domain, stats in domain_stats.items():
        kw_count = len(set(stats["keywords"]))
        visibility = _compute_visibility(stats["positions"])
        database.upsert_competitor(domain, today, kw_count, visibility)
        for kw, pos in zip(stats["keywords"], stats["positions"]):
            database.upsert_competitor_keyword(domain, kw, pos, today)
        summary[domain] = {
            "keyword_count": kw_count,
            "visibility_score": visibility,
            "keywords": list(set(stats["keywords"])),
        }

    log.info("Competitor tracking complete for %d domains", len(summary))
    return summary


def compute_ranking_changes(domain: str) -> list[dict]:
    """
    Return day-over-day ranking changes for *domain*.

    Returns a list of dicts: [{date, keyword_count, visibility_score, delta_kw, delta_vis}]
    """
    history = database.get_competitor_history(domain)
    if len(history) < 2:
        return history

    enriched = []
    for i, record in enumerate(history):
        if i == 0:
            enriched.append({**record, "delta_kw": 0, "delta_vis": 0.0})
        else:
            prev = history[i - 1]
            enriched.append(
                {
                    **record,
                    "delta_kw": record["keyword_count"] - prev["keyword_count"],
                    "delta_vis": round(
                        record["visibility_score"] - prev["visibility_score"], 2
                    ),
                }
            )
    return enriched


def get_top_competitors(limit: int = 20) -> list[dict]:
    """Return the top *limit* competitors sorted by current visibility score."""
    return database.get_all_competitors()[:limit]
