"""
Report generation module.

Generates reports in:
    - Markdown (.md)
    - CSV (.csv)
    - JSON (.json)
    - HTML dashboard (.html)

All reports are written to the REPORTS_DIR directory with a date-stamped filename.
"""

import csv
import json
from datetime import date
from pathlib import Path

from config import REPORTS_DIR
from seo_intelligence import database
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

_TODAY = date.today().isoformat()


def _report_path(name: str, ext: str) -> Path:
    return REPORTS_DIR / f"{name}_{_TODAY}.{ext}"


# ── Markdown ───────────────────────────────────────────────────────────────────

def generate_markdown_report(
    keywords: list[dict],
    competitors: list[dict],
    gaps: list[dict],
    limit: int = 50,
) -> Path:
    """Generate a Markdown report and return the file path."""
    path = _report_path("seo_report", "md")
    lines: list[str] = [
        f"# SEO Intelligence Report — Uganda Web Design\n",
        f"**Generated:** {_TODAY}\n",
        "\n---\n",
        "## Top Keyword Opportunities\n",
        "| Keyword | Intent | Trend Score | Opportunity Score |",
        "|---------|--------|-------------|-------------------|",
    ]
    for kw in sorted(keywords, key=lambda k: k.get("opportunity_score", 0), reverse=True)[:limit]:
        lines.append(
            f"| {kw['keyword']} | {kw.get('intent','–')} "
            f"| {kw.get('trend_score', 0):.1f} | {kw.get('opportunity_score', 0):.1f} |"
        )

    lines += [
        "\n---\n",
        "## Competitor Visibility\n",
        "| Domain | Keywords Ranked | Visibility Score |",
        "|--------|----------------|-----------------|",
    ]
    for c in competitors[:20]:
        lines.append(
            f"| {c['domain']} | {c.get('keyword_count', 0)} | {c.get('visibility_score', 0):.1f} |"
        )

    lines += [
        "\n---\n",
        "## Content Gaps\n",
    ]
    for g in gaps[:20]:
        lines.append(f"### {g['topic']}\n")
        lines.append(f"**Keywords:** {g.get('keywords', '–')}\n")
        lines.append(f"**Recommendation:** {g.get('recommendation', '–')}\n")

    path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Markdown report written to %s", path)
    return path


# ── CSV ────────────────────────────────────────────────────────────────────────

def generate_csv_report(keywords: list[dict]) -> Path:
    """Write all keywords to a CSV file and return the file path."""
    path = _report_path("keywords", "csv")
    if not keywords:
        path.write_text("", encoding="utf-8")
        return path

    fieldnames = list(keywords[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(keywords)

    log.info("CSV report written to %s (%d rows)", path, len(keywords))
    return path


# ── JSON ───────────────────────────────────────────────────────────────────────

def generate_json_report(
    keywords: list[dict],
    competitors: list[dict],
    gaps: list[dict],
) -> Path:
    """Write a structured JSON report and return the file path."""
    path = _report_path("seo_report", "json")
    payload = {
        "generated": _TODAY,
        "country": "Uganda",
        "keyword_count": len(keywords),
        "top_opportunities": sorted(
            keywords, key=lambda k: k.get("opportunity_score", 0), reverse=True
        )[:100],
        "competitors": competitors[:50],
        "content_gaps": gaps[:50],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("JSON report written to %s", path)
    return path


# ── HTML Dashboard ─────────────────────────────────────────────────────────────

def generate_html_report(
    keywords: list[dict],
    competitors: list[dict],
    gaps: list[dict],
) -> Path:
    """Generate a self-contained HTML dashboard and return the file path."""
    path = _report_path("dashboard", "html")

    top_kws = sorted(keywords, key=lambda k: k.get("opportunity_score", 0), reverse=True)[:50]
    trend_kws = sorted(keywords, key=lambda k: k.get("trend_score", 0), reverse=True)[:50]

    def kw_rows(kws: list[dict]) -> str:
        rows = []
        for k in kws:
            score = k.get("opportunity_score", 0)
            colour = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
            rows.append(
                f"<tr><td>{k['keyword']}</td><td>{k.get('intent','–')}</td>"
                f"<td>{k.get('trend_score',0):.1f}</td>"
                f"<td style='color:{colour};font-weight:700'>{score:.1f}</td></tr>"
            )
        return "\n".join(rows)

    def comp_rows(comps: list[dict]) -> str:
        return "\n".join(
            f"<tr><td>{c['domain']}</td><td>{c.get('keyword_count',0)}</td>"
            f"<td>{c.get('visibility_score',0):.1f}</td></tr>"
            for c in comps[:20]
        )

    def gap_cards(g_list: list[dict]) -> str:
        cards = []
        for g in g_list[:10]:
            cards.append(
                f"<div class='gap-card'>"
                f"<h3>{g['topic']}</h3>"
                f"<p><strong>Keywords:</strong> {g.get('keywords','–')}</p>"
                f"<p>{g.get('recommendation','')}</p>"
                f"</div>"
            )
        return "\n".join(cards)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SEO Intelligence Dashboard — Uganda {_TODAY}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
  header {{ background: #1e293b; padding: 1.5rem 2rem; border-bottom: 1px solid #334155; }}
  header h1 {{ font-size: 1.5rem; color: #38bdf8; }}
  header p  {{ color: #94a3b8; font-size: .875rem; margin-top: .25rem; }}
  .stats {{ display: flex; gap: 1rem; padding: 1.5rem 2rem; flex-wrap: wrap; }}
  .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px;
           padding: 1rem 1.5rem; flex: 1; min-width: 160px; }}
  .stat .value {{ font-size: 2rem; font-weight: 700; color: #38bdf8; }}
  .stat .label {{ font-size: .75rem; color: #94a3b8; margin-top: .25rem; }}
  section {{ padding: 1.5rem 2rem; }}
  h2 {{ font-size: 1.125rem; color: #38bdf8; margin-bottom: 1rem;
        border-left: 3px solid #38bdf8; padding-left: .75rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .875rem; }}
  th {{ background: #1e293b; color: #94a3b8; text-align: left;
        padding: .5rem .75rem; border-bottom: 1px solid #334155; }}
  td {{ padding: .5rem .75rem; border-bottom: 1px solid #1e293b; }}
  tr:nth-child(even) td {{ background: #0f172a; }}
  tr:hover td {{ background: #1e293b; }}
  .gap-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px;
               padding: 1rem 1.25rem; margin-bottom: .75rem; }}
  .gap-card h3 {{ color: #fbbf24; font-size: .95rem; margin-bottom: .5rem; }}
  .gap-card p  {{ font-size: .8rem; color: #94a3b8; margin-top: .25rem; }}
  .tabs {{ display: flex; gap: .5rem; margin-bottom: 1rem; }}
  .tab  {{ padding: .375rem .875rem; border-radius: 6px; cursor: pointer;
           background: #1e293b; border: 1px solid #334155; color: #94a3b8;
           font-size: .8rem; }}
  .tab.active {{ background: #38bdf8; color: #0f172a; border-color: #38bdf8; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <h1>🇺🇬 SEO Intelligence Dashboard — Uganda Web Design</h1>
  <p>Generated {_TODAY} · {len(keywords)} keywords tracked · {len(competitors)} competitors monitored</p>
</header>

<div class="stats">
  <div class="stat"><div class="value">{len(keywords)}</div><div class="label">Total Keywords</div></div>
  <div class="stat"><div class="value">{len([k for k in keywords if k.get('opportunity_score',0)>=70])}</div><div class="label">High-Opportunity Keywords</div></div>
  <div class="stat"><div class="value">{len(competitors)}</div><div class="label">Competitors Tracked</div></div>
  <div class="stat"><div class="value">{len(gaps)}</div><div class="label">Content Gaps Found</div></div>
</div>

<section>
  <h2>Top Opportunities</h2>
  <table>
    <thead><tr><th>Keyword</th><th>Intent</th><th>Trend Score</th><th>Opportunity Score</th></tr></thead>
    <tbody>{kw_rows(top_kws)}</tbody>
  </table>
</section>

<section>
  <h2>Trending Keywords</h2>
  <table>
    <thead><tr><th>Keyword</th><th>Intent</th><th>Trend Score</th><th>Opportunity Score</th></tr></thead>
    <tbody>{kw_rows(trend_kws)}</tbody>
  </table>
</section>

<section>
  <h2>Competitor Visibility</h2>
  <table>
    <thead><tr><th>Domain</th><th>Keywords Ranked</th><th>Visibility Score</th></tr></thead>
    <tbody>{comp_rows(competitors)}</tbody>
  </table>
</section>

<section>
  <h2>Content Gaps &amp; Recommendations</h2>
  {gap_cards(gaps)}
</section>

</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    log.info("HTML dashboard written to %s", path)
    return path


# ── Orchestrator ───────────────────────────────────────────────────────────────

def generate_all_reports() -> dict[str, Path]:
    """
    Generate all report formats from the current database state.

    Returns a dict mapping format name → file path.
    """
    log.info("Generating all reports…")
    keywords = database.get_all_keywords()
    competitors = database.get_all_competitors()
    gaps = database.get_content_gaps()

    paths: dict[str, Path] = {
        "markdown": generate_markdown_report(keywords, competitors, gaps),
        "csv": generate_csv_report(keywords),
        "json": generate_json_report(keywords, competitors, gaps),
        "html": generate_html_report(keywords, competitors, gaps),
    }
    log.info("All reports generated: %s", {k: str(v) for k, v in paths.items()})
    return paths
