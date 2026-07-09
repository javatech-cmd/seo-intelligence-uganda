"""
Content gap analysis module.

Compares what top-ranking pages cover versus what is missing.
Generates concrete recommendations for topics that no competitor
has addressed (or has addressed poorly).

Uganda-specific gap examples
-----------------------------
- Mobile Money integration
- URA e-invoicing
- Payment plans
- Maintenance contracts
- Local hosting options
"""

from collections import Counter
from datetime import date

from seo_intelligence import database
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

# Anchor topics that are known to be underserved in the Ugandan market
_UGANDAN_OPPORTUNITY_TOPICS: list[dict] = [
    {
        "topic": "Mobile Money integration for websites",
        "keywords": ["mobile money website", "MTN Mobile Money integration", "Airtel Money payment gateway"],
        "recommendation": (
            "Create a comprehensive guide on integrating MTN Mobile Money and Airtel Money "
            "payment gateways into Ugandan business websites. Cover API setup, sandbox testing, "
            "and go-live checklist."
        ),
    },
    {
        "topic": "URA e-invoicing integration",
        "keywords": ["URA e-invoicing website", "EFRIS integration Uganda", "e-invoicing system Uganda"],
        "recommendation": (
            "Write a technical guide explaining how to integrate the Uganda Revenue Authority "
            "EFRIS e-invoicing system into WooCommerce and custom websites."
        ),
    },
    {
        "topic": "Website payment plans Uganda",
        "keywords": ["website payment plans Uganda", "website installment Uganda", "website deposit Uganda"],
        "recommendation": (
            "Publish a pricing and payment-plan explainer showing flexible instalment options "
            "for Ugandan SMEs who cannot afford a lump-sum website fee."
        ),
    },
    {
        "topic": "Website maintenance contracts Uganda",
        "keywords": ["website maintenance plan Uganda", "monthly website support Uganda"],
        "recommendation": (
            "Create a landing page and comparison guide for monthly website maintenance "
            "contracts, including what is covered (security, backups, updates, uptime monitoring)."
        ),
    },
    {
        "topic": "Local Ugandan web hosting options",
        "keywords": ["ugandan web hosting", "hosting in Uganda", "local hosting kampala"],
        "recommendation": (
            "Publish a comparison of local Ugandan hosting providers vs international ones, "
            "covering speed for local users, cost in UGX, and support quality."
        ),
    },
    {
        "topic": "Website costs in Uganda 2024",
        "keywords": ["how much does a website cost in Uganda", "website price Uganda", "website budget Uganda"],
        "recommendation": (
            "Publish a transparent, up-to-date pricing guide breaking down website costs "
            "by type (landing page, SME site, e-commerce) with UGX prices."
        ),
    },
    {
        "topic": "WordPress vs custom website Uganda",
        "keywords": ["wordpress vs custom website Uganda", "should I use wordpress Uganda"],
        "recommendation": (
            "Create a decision-guide article comparing WordPress and custom-built websites "
            "from the perspective of a Ugandan business owner."
        ),
    },
]


def _extract_heading_tokens(page_analyses: list[dict]) -> Counter:
    """
    Tokenise all H2 and H3 headings from *page_analyses* and count frequencies.
    """
    tokens: Counter = Counter()
    for page in page_analyses:
        for field in ("h2s", "h3s"):
            for heading in (page.get(field) or "").split("|"):
                for word in heading.lower().split():
                    if len(word) > 3:
                        tokens[word] += 1
    return tokens


def _coverage_score(topic_keywords: list[str], heading_tokens: Counter) -> float:
    """
    Return a 0–1 score indicating how well top-ranking pages cover *topic_keywords*.

    0 = nobody covers this → high gap.
    1 = well covered → low gap.
    """
    if not topic_keywords:
        return 1.0
    hits = sum(
        1
        for kw in topic_keywords
        for word in kw.lower().split()
        if heading_tokens.get(word, 0) > 0
    )
    return hits / sum(len(kw.split()) for kw in topic_keywords)


def analyse_content_gaps(
    serp_data: dict[str, list[dict]],
    page_analyses: list[dict],
) -> list[dict]:
    """
    Detect and persist content gaps.

    Parameters
    ----------
    serp_data:
        Mapping of keyword → list of SERP result dicts.
    page_analyses:
        List of page analysis dicts collected for all ranking URLs.

    Returns
    -------
    list[dict]
        Gaps sorted by coverage score (lowest first = highest opportunity).
    """
    today = date.today().isoformat()
    heading_tokens = _extract_heading_tokens(page_analyses)

    gaps: list[dict] = []

    for opportunity in _UGANDAN_OPPORTUNITY_TOPICS:
        coverage = _coverage_score(opportunity["keywords"], heading_tokens)
        gap_score = round(1.0 - coverage, 4)

        gap = {
            "topic": opportunity["topic"],
            "date": today,
            "keywords": ", ".join(opportunity["keywords"]),
            "recommendation": opportunity["recommendation"],
            "coverage_score": coverage,
            "gap_score": gap_score,
        }
        gaps.append(gap)

        database.upsert_content_gap(
            opportunity["topic"],
            today,
            ", ".join(opportunity["keywords"]),
            opportunity["recommendation"],
        )

    # Also auto-detect gaps from heading frequency analysis
    all_keywords = list(serp_data.keys())
    covered_words = {w for w, count in heading_tokens.items() if count >= 2}

    for kw in all_keywords:
        kw_words = set(kw.lower().split())
        if len(kw_words) >= 2 and not kw_words.intersection(covered_words):
            topic = f"Uncovered topic: {kw}"
            rec = (
                f"No top-ranking page addresses '{kw}'. "
                "Consider creating targeted content for this keyword."
            )
            database.upsert_content_gap(topic, today, kw, rec)
            gaps.append(
                {
                    "topic": topic,
                    "date": today,
                    "keywords": kw,
                    "recommendation": rec,
                    "coverage_score": 0.0,
                    "gap_score": 1.0,
                }
            )

    gaps.sort(key=lambda g: g["gap_score"], reverse=True)
    log.info("Content gap analysis complete: %d gaps identified", len(gaps))
    return gaps
