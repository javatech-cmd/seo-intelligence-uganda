"""
AI content brief generator.

Generates structured article briefs for high-opportunity keywords.

Without OpenAI credentials, a rule-based brief is generated from the
collected SERP and page-analysis data.

With OPENAI_API_KEY set, GPT is used to enrich the outline, FAQs, and
internal links with natural language suggestions.
"""

import json
import re
from datetime import date

from config import OPENAI_API_KEY, OPENAI_MODEL
from seo_intelligence import database
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

_READING_WPM = 238


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def _estimate_word_count(competitor_pages: list[dict]) -> int:
    if not competitor_pages:
        return 1500
    avg = sum(p.get("word_count", 0) for p in competitor_pages) / len(competitor_pages)
    # Aim 20 % above average to outperform competitors
    return max(int(avg * 1.2), 1000)


def _collect_h2_ideas(keyword: str, competitor_pages: list[dict]) -> list[str]:
    """Extract common H2 headings from competitor pages and add original ones."""
    seen: set[str] = set()
    h2s: list[str] = []
    for page in competitor_pages:
        for heading in (page.get("h2s") or "").split("|"):
            heading = heading.strip()
            if heading and heading.lower() not in seen:
                seen.add(heading.lower())
                h2s.append(heading)
    # Always suggest at least these structural headings
    defaults = [
        f"What is {keyword}?",
        f"Why does your business need {keyword}?",
        f"How much does {keyword} cost in Uganda?",
        "How to get started",
        "Frequently asked questions",
    ]
    for d in defaults:
        if d.lower() not in seen:
            h2s.append(d)
    return h2s[:10]


def _collect_faq_ideas(keyword: str, competitor_pages: list[dict]) -> list[str]:
    faqs = [
        f"How much does {keyword} cost in Uganda?",
        f"How long does it take to build a {keyword}?",
        f"What do I need to get started with {keyword}?",
        f"Can I pay in installments for {keyword}?",
        f"Do you support Mobile Money payments for {keyword}?",
        f"Is {keyword} available in Kampala?",
    ]
    return faqs


def _infer_schema(keyword: str, competitor_pages: list[dict]) -> list[str]:
    schemas = {"Article", "FAQPage"}
    for page in competitor_pages:
        for stype in (page.get("schema_types") or "").split(","):
            stype = stype.strip()
            if stype:
                schemas.add(stype)
    # Recommend LocalBusiness schema for Uganda-focused content
    schemas.add("LocalBusiness")
    return sorted(schemas)


def _rule_based_brief(keyword: str, competitor_pages: list[dict]) -> dict:
    """Generate a content brief without calling any external API."""
    h2s = _collect_h2_ideas(keyword, competitor_pages)
    faqs = _collect_faq_ideas(keyword, competitor_pages)
    schema_types = _infer_schema(keyword, competitor_pages)
    word_count = _estimate_word_count(competitor_pages)
    slug = _slugify(keyword)
    title = keyword.title()
    meta = (
        f"Everything you need to know about {keyword} in Uganda. "
        f"Compare prices, services, and find the best providers in Kampala."
    )[:160]

    outline = (
        f"1. Introduction to {keyword}\n"
        "2. " + "\n".join(f"{i + 2}. {h}" for i, h in enumerate(h2s[1:])) + "\n"
        f"{len(h2s) + 1}. Conclusion and next steps"
    )

    return {
        "keyword": keyword,
        "date": date.today().isoformat(),
        "title": title,
        "meta_description": meta,
        "slug": slug,
        "outline": outline,
        "suggested_h2s": json.dumps(h2s, ensure_ascii=False),
        "suggested_faqs": json.dumps(faqs, ensure_ascii=False),
        "suggested_schema": json.dumps(schema_types, ensure_ascii=False),
        "suggested_internal_links": json.dumps([], ensure_ascii=False),
        "estimated_word_count": word_count,
    }


def _openai_enriched_brief(keyword: str, rule_brief: dict) -> dict:
    """Enrich a rule-based brief with GPT-generated language (if key available)."""
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""You are a senior SEO content strategist specialising in Uganda.
Generate a content brief for the keyword: "{keyword}"

The target audience is Ugandan business owners looking for web design services.
Focus on Uganda-specific context: Mobile Money, Kampala businesses, local pricing in UGX.

Return ONLY valid JSON with these keys:
- title (string, <60 chars)
- meta_description (string, <155 chars)
- outline (string, numbered outline)
- suggested_h2s (array of strings, 6–8 items)
- suggested_faqs (array of question strings, 5–7 items)
- suggested_schema (array of schema @type strings)
- suggested_internal_links (array of suggested slug strings)
- estimated_word_count (integer)"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=1500,
        )
        data = json.loads(response.choices[0].message.content)
        # Merge into rule brief, overwriting with AI values
        for key in (
            "title", "meta_description", "outline",
            "suggested_h2s", "suggested_faqs",
            "suggested_schema", "suggested_internal_links",
            "estimated_word_count",
        ):
            if key in data:
                val = data[key]
                rule_brief[key] = json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict)) else val
        log.info("OpenAI brief generated for '%s'", keyword)
    except Exception as exc:
        log.warning("OpenAI brief enrichment failed for '%s': %s — using rule-based", keyword, exc)
    return rule_brief


def generate_brief(keyword: str, competitor_pages: list[dict] | None = None) -> dict:
    """
    Generate a content brief for *keyword*.

    Parameters
    ----------
    keyword:
        The target keyword to build the brief around.
    competitor_pages:
        Optional list of page-analysis dicts for competing pages.
        Fetched from the database if not provided.

    Returns
    -------
    dict
        The content brief (also persisted to the database).
    """
    if competitor_pages is None:
        competitor_pages = []

    brief = _rule_based_brief(keyword, competitor_pages)
    if OPENAI_API_KEY:
        brief = _openai_enriched_brief(keyword, brief)

    database.upsert_content_brief(brief)
    return brief


def generate_briefs_for_top_keywords(limit: int = 20) -> list[dict]:
    """
    Generate content briefs for the top *limit* highest-opportunity keywords.

    Returns the list of generated briefs.
    """
    top_kws = database.get_all_keywords(limit=limit)
    briefs: list[dict] = []
    for kw_data in top_kws:
        kw = kw_data["keyword"]
        # Load page analyses for ranking URLs
        from seo_intelligence.database import get_serp_results, get_page_analysis

        serp = get_serp_results(kw)
        pages = [
            pa
            for r in serp
            if (pa := get_page_analysis(r["url"])) is not None
        ]
        try:
            brief = generate_brief(kw, pages)
            briefs.append(brief)
            log.info("Brief generated for '%s'", kw)
        except Exception as exc:
            log.warning("Brief generation failed for '%s': %s", kw, exc)
    return briefs
