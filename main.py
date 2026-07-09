"""
SEO Intelligence Platform — CLI entry point.

Usage
-----
    python main.py discover          # Run keyword discovery only
    python main.py trends            # Update Google Trends scores
    python main.py serp              # Run SERP analysis for all keywords
    python main.py pages             # Analyse ranking pages
    python main.py competitors       # Update competitor tracking
    python main.py gaps              # Run content gap analysis
    python main.py briefs            # Generate AI content briefs
    python main.py reports           # Generate all reports
    python main.py run               # Run the full pipeline (default)
    python main.py --help            # Show this help
"""

import argparse
import sys
from datetime import date

from seo_intelligence.logger import get_logger

log = get_logger(__name__)


def _init() -> None:
    """Ensure the database exists before any module tries to use it."""
    from seo_intelligence.database import init_db
    init_db()


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover keywords from Google Suggest, related searches, and PAA."""
    from seo_intelligence.keyword_discovery import discover_keywords
    from config import SEED_KEYWORDS

    seeds = SEED_KEYWORDS
    keywords = discover_keywords(seeds)
    log.info("Keyword discovery complete: %d keywords found", len(keywords))


def cmd_trends(args: argparse.Namespace) -> None:
    """Fetch Google Trends interest scores for all stored keywords."""
    from seo_intelligence.database import get_distinct_keywords_latest
    from seo_intelligence.google_trends_module import update_trend_scores

    kws = [row["keyword"] for row in get_distinct_keywords_latest(limit=500)]
    if not kws:
        log.warning("No keywords in DB — run 'discover' first.")
        return
    update_trend_scores(kws)


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify keyword intent for all stored keywords."""
    from seo_intelligence.database import get_distinct_keywords_latest, upsert_keyword
    from seo_intelligence.keyword_classifier import classify_many

    today = date.today().isoformat()
    rows = get_distinct_keywords_latest(limit=10000)
    keywords = [r["keyword"] for r in rows]
    results = classify_many(keywords)
    for row, result in zip(rows, results):
        upsert_keyword(
            row["keyword"],
            today,
            trend_score=row.get("trend_score", 0.0),
            source=row.get("source", ""),
            intent=result.intent.value,
            opportunity_score=row.get("opportunity_score", 0.0),
        )
    log.info("Intent classification complete for %d keywords", len(results))


def cmd_serp(args: argparse.Namespace) -> None:
    """Run SERP analysis for all stored keywords."""
    from seo_intelligence.database import get_distinct_keywords_latest
    from seo_intelligence.serp_analysis import analyse_serp

    rows = get_distinct_keywords_latest(limit=200)
    kws = [r["keyword"] for r in rows]
    if not kws:
        log.warning("No keywords in DB — run 'discover' first.")
        return
    analyse_serp(kws)


def cmd_pages(args: argparse.Namespace) -> None:
    """Visit and analyse every URL collected from today's SERP results."""
    from seo_intelligence.database import get_distinct_keywords_latest, get_serp_results_for_date
    from seo_intelligence.page_analysis import analyse_pages

    today = date.today().isoformat()
    rows = get_distinct_keywords_latest(limit=200)
    urls: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for r in get_serp_results_for_date(row["keyword"], today):
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)

    if not urls:
        log.warning("No SERP URLs for today in DB — run 'serp' first.")
        return
    log.info("Analysing %d unique URLs", len(urls))
    analyse_pages(urls)


def cmd_competitors(args: argparse.Namespace) -> None:
    """Update competitor tracking from today's SERP data."""
    from seo_intelligence.database import get_distinct_keywords_latest, get_serp_results_for_date
    from seo_intelligence.competitor_tracker import track_competitors

    today = date.today().isoformat()
    rows = get_distinct_keywords_latest(limit=1000)
    serp_data: dict[str, list[dict]] = {}
    for row in rows:
        kw = row["keyword"]
        results = get_serp_results_for_date(kw, today)
        if results:
            serp_data[kw] = results

    if not serp_data:
        log.warning("No SERP data for today in DB — run 'serp' first.")
        return
    summary = track_competitors(serp_data)
    log.info("Tracked %d competitor domains", len(summary))


def cmd_gaps(args: argparse.Namespace) -> None:
    """Run content gap analysis using today's SERP data."""
    from seo_intelligence.database import (
        get_distinct_keywords_latest, get_serp_results_for_date, get_page_analysis
    )
    from seo_intelligence.content_gap import analyse_content_gaps

    today = date.today().isoformat()
    rows = get_distinct_keywords_latest(limit=500)
    serp_data: dict[str, list[dict]] = {}
    for row in rows:
        kw = row["keyword"]
        results = get_serp_results_for_date(kw, today)
        if results:
            serp_data[kw] = results

    # Collect page analyses for ranking URLs
    all_pages: list[dict] = []
    seen_urls: set[str] = set()
    for kw_results in serp_data.values():
        for r in kw_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                pa = get_page_analysis(url)
                if pa:
                    all_pages.append(pa)

    gaps = analyse_content_gaps(serp_data, all_pages)
    log.info("Content gap analysis identified %d gaps", len(gaps))


def cmd_score(args: argparse.Namespace) -> None:
    """Compute and update opportunity scores for all keywords (latest row per keyword)."""
    from seo_intelligence.database import (
        get_distinct_keywords_latest, get_serp_results_for_date, get_page_analysis, upsert_keyword
    )
    from seo_intelligence.opportunity_scorer import score_keyword

    today = date.today().isoformat()
    rows = get_distinct_keywords_latest(limit=5000)

    for row in rows:
        kw = row["keyword"]
        # Use today's SERP results; fall back to the most recent available date
        serp = get_serp_results_for_date(kw, today)
        if not serp:
            from seo_intelligence.database import get_serp_results
            serp = get_serp_results(kw)[:10]  # most-recent-date results
        pages = [
            pa
            for r in serp
            if (pa := get_page_analysis(r.get("url", ""))) is not None
        ]
        score = score_keyword(row, serp, pages)
        upsert_keyword(
            kw,
            today,
            trend_score=row.get("trend_score", 0.0),
            source=row.get("source", ""),
            intent=row.get("intent", ""),
            opportunity_score=score,
        )

    log.info("Opportunity scores updated for %d keywords", len(rows))


def cmd_briefs(args: argparse.Namespace) -> None:
    """Generate AI content briefs for top-opportunity keywords."""
    from seo_intelligence.content_brief import generate_briefs_for_top_keywords
    limit = getattr(args, "limit", 20)
    briefs = generate_briefs_for_top_keywords(limit=limit)
    log.info("Generated %d content briefs", len(briefs))


def cmd_reports(args: argparse.Namespace) -> None:
    """Generate all report formats from current database state."""
    from seo_intelligence.report_generator import generate_all_reports
    paths = generate_all_reports()
    for fmt, path in paths.items():
        log.info("Report [%s]: %s", fmt, path)


def cmd_run(args: argparse.Namespace) -> None:
    """Execute the full pipeline end-to-end."""
    log.info("=" * 60)
    log.info("SEO Intelligence Platform — Full Pipeline")
    log.info("Date: %s | Country: Uganda", date.today().isoformat())
    log.info("=" * 60)

    steps = [
        ("Keyword Discovery",      cmd_discover),
        ("Google Trends",          cmd_trends),
        ("Intent Classification",  cmd_classify),
        ("SERP Analysis",          cmd_serp),
        ("Page Analysis",          cmd_pages),
        ("Competitor Tracking",    cmd_competitors),
        ("Content Gap Analysis",   cmd_gaps),
        ("Opportunity Scoring",    cmd_score),
        ("Content Briefs",         cmd_briefs),
        ("Report Generation",      cmd_reports),
    ]

    for step_name, step_fn in steps:
        log.info("── Step: %s ──", step_name)
        try:
            step_fn(args)
        except Exception as exc:
            log.error("Step '%s' failed: %s — continuing", step_name, exc)

    log.info("=" * 60)
    log.info("Full pipeline complete.")
    log.info("=" * 60)


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo_platform",
        description="SEO Intelligence Platform for Uganda's web design market.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("discover",    help="Discover keywords via autocomplete & related searches")
    sub.add_parser("trends",      help="Update Google Trends interest scores")
    sub.add_parser("classify",    help="Classify keyword intent (Informational / Transactional / …)")
    sub.add_parser("serp",        help="Run SERP analysis for stored keywords")
    sub.add_parser("pages",       help="Analyse ranking pages")
    sub.add_parser("competitors", help="Update competitor tracking")
    sub.add_parser("gaps",        help="Run content gap analysis")
    sub.add_parser("score",       help="Compute opportunity scores")
    briefs_p = sub.add_parser("briefs", help="Generate AI content briefs")
    briefs_p.add_argument("--limit", type=int, default=20, help="Number of keywords to brief")
    sub.add_parser("reports",     help="Generate all reports (Markdown, CSV, JSON, HTML)")
    sub.add_parser("run",         help="Execute the full pipeline (default)")

    return parser


def main() -> int:
    _init()
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "discover":    cmd_discover,
        "trends":      cmd_trends,
        "classify":    cmd_classify,
        "serp":        cmd_serp,
        "pages":       cmd_pages,
        "competitors": cmd_competitors,
        "gaps":        cmd_gaps,
        "score":       cmd_score,
        "briefs":      cmd_briefs,
        "reports":     cmd_reports,
        "run":         cmd_run,
        None:          cmd_run,
    }

    fn = commands.get(args.command)
    if fn is None:
        parser.print_help()
        return 1

    try:
        fn(args)
        return 0
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        return 130
    except Exception as exc:
        log.error("Unhandled error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
