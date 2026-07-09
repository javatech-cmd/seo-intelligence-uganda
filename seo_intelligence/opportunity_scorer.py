"""
Opportunity scoring module.

Produces a score between 0 and 100 for each keyword.

Score components
----------------
trend_score         (0–100 from Google Trends)   → weighted 25 %
intent_score        (buyer intent proxy)          → weighted 20 %
competition_score   (inverse of competitor count) → weighted 25 %
content_quality_inv (inverse avg quality of SERPs)→ weighted 15 %
serp_weakness       (computed by serp_analysis)   → weighted 15 %
"""

from config import (
    SCORE_WEIGHT_COMPETITION,
    SCORE_WEIGHT_CONTENT_QUALITY,
    SCORE_WEIGHT_INTENT,
    SCORE_WEIGHT_SERP_WEAKNESS,
    SCORE_WEIGHT_TREND,
)
from seo_intelligence.keyword_classifier import Intent
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

# Buyer intent scores per intent class (0 = lowest, 1 = highest)
_INTENT_SCORES: dict[str, float] = {
    Intent.TRANSACTIONAL: 1.00,
    Intent.COMMERCIAL: 0.80,
    Intent.LOCAL: 0.75,
    Intent.NAVIGATIONAL: 0.40,
    Intent.QUESTION: 0.30,
    Intent.INFORMATIONAL: 0.20,
}


def _normalise_trend(trend_score: float) -> float:
    """Map a 0–100 pytrends score to 0–1."""
    return min(max(trend_score, 0.0), 100.0) / 100.0


def _competition_score(num_competitors: int) -> float:
    """
    Convert number of unique competitor domains in top-10 to a 0–1 score.

    Fewer unique domains → higher opportunity.
    """
    # 1 competitor  → 0.90, 5 → 0.50, 10 → 0.10
    return max(0.0, 1.0 - (num_competitors - 1) * 0.10)


def compute_opportunity_score(
    trend_score: float,
    intent: str,
    num_competitors: int,
    avg_content_quality: float,  # 0–100
    serp_weakness: float,        # 0–1
) -> float:
    """
    Compute the opportunity score (0–100) for a keyword.

    Parameters
    ----------
    trend_score:
        Average Google Trends interest (0–100).
    intent:
        One of the Intent enum values.
    num_competitors:
        Number of unique competitor domains in the top-10 SERP.
    avg_content_quality:
        Average content quality score (0–100) of top-ranking pages.
    serp_weakness:
        SERP weakness score (0–1) from :func:`serp_analysis.compute_serp_weakness`.

    Returns
    -------
    float
        Opportunity score clamped to [0, 100].
    """
    t = _normalise_trend(trend_score)
    i = _INTENT_SCORES.get(intent, 0.20)
    c = _competition_score(num_competitors)
    q = max(0.0, 1.0 - avg_content_quality / 100.0)  # low quality → high opportunity
    w = min(max(serp_weakness, 0.0), 1.0)

    raw = (
        t * SCORE_WEIGHT_TREND
        + i * SCORE_WEIGHT_INTENT
        + c * SCORE_WEIGHT_COMPETITION
        + q * SCORE_WEIGHT_CONTENT_QUALITY
        + w * SCORE_WEIGHT_SERP_WEAKNESS
    )
    return round(raw * 100.0, 2)


def score_keyword(keyword_data: dict, serp_results: list[dict], page_analyses: list[dict]) -> float:
    """
    High-level helper: derive all inputs from stored data and return the score.

    Parameters
    ----------
    keyword_data:
        A dict from :func:`database.get_all_keywords` (must include ``trend_score``, ``intent``).
    serp_results:
        List of SERP result dicts for the keyword.
    page_analyses:
        List of page analysis dicts for the ranking URLs.
    """
    from seo_intelligence.serp_analysis import compute_serp_weakness

    trend = keyword_data.get("trend_score", 0.0)
    intent = keyword_data.get("intent", Intent.INFORMATIONAL)
    unique_domains = len(set(r.get("domain", "") for r in serp_results))
    avg_quality = (
        sum(p.get("content_quality_score", 0) for p in page_analyses) / len(page_analyses)
        if page_analyses
        else 50.0
    )
    weakness = compute_serp_weakness(serp_results, page_analyses)

    score = compute_opportunity_score(trend, intent, unique_domains, avg_quality, weakness)
    log.debug(
        "Opportunity score for '%s': %.1f (trend=%.1f intent=%s comp=%d quality=%.1f weakness=%.2f)",
        keyword_data.get("keyword", "?"),
        score,
        trend,
        intent,
        unique_domains,
        avg_quality,
        weakness,
    )
    return score
