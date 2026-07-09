# SEO Intelligence Platform 🇺🇬

A production-quality SEO research engine built specifically for the **Ugandan web design industry**.

Think of it as a miniature Ahrefs/SEMrush focused entirely on Uganda's website design market — designed to discover opportunities that competing agencies have not yet targeted and automatically recommend content that can outrank them.

---

## Features

| Module | Description |
|--------|-------------|
| **Keyword Discovery** | Google Suggest autocomplete + alphabet expansion (a–z per seed) + PAA |
| **Google Trends** | Interest-over-time scores restricted to Uganda (`geo=UG`) |
| **Intent Classification** | Rule-based: Informational · Commercial · Transactional · Navigational · Local · Question |
| **SERP Analysis** | Google CSE API → DataForSEO → HTML scraping fallback |
| **Page Analysis** | H1/H2/H3, word count, images, tables, FAQs, JSON-LD schema, OG tags, quality score |
| **Competitor Tracking** | Per-domain keyword counts, visibility scores, ranking deltas |
| **Content Gap Analysis** | Identifies uncovered topics (Mobile Money, URA e-invoicing, etc.) |
| **Opportunity Scoring** | Weighted 0–100 score per keyword |
| **Content Briefs** | Rule-based article briefs + optional OpenAI enrichment |
| **Reports** | Markdown · CSV · JSON · HTML dashboard |
| **GitHub Actions** | Daily automated pipeline; reports stored as workflow artifacts |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-org/seo-intelligence-uganda.git
cd seo-intelligence-uganda
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your API keys (all optional — see below)
```

### 3. Run

```bash
# Full pipeline
python main.py run

# Individual steps
python main.py discover     # keyword discovery
python main.py trends       # Google Trends scores
python main.py classify     # intent classification
python main.py serp         # SERP analysis
python main.py pages        # page analysis
python main.py competitors  # competitor tracking
python main.py gaps         # content gap analysis
python main.py score        # opportunity scoring
python main.py briefs       # content brief generation
python main.py reports      # generate all reports
```

---

## API Keys (all optional)

| Key | Purpose | Where to get it |
|-----|---------|-----------------|
| `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` | SERP data (preferred) | [Google CSE](https://programmablesearchengine.google.com/) + [GCP Console](https://console.cloud.google.com/) |
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Premium SERP fallback | [dataforseo.com](https://dataforseo.com/) |
| `OPENAI_API_KEY` | Enriched content briefs | [platform.openai.com](https://platform.openai.com/) |

Without any API keys the platform falls back to free HTML scraping. Google Trends data is always free (via pytrends).

---

## Output

All outputs are written to:

| Path | Content |
|------|---------|
| `data/seo_intelligence.db` | SQLite database (all historical data) |
| `reports/seo_report_YYYY-MM-DD.md` | Markdown report |
| `reports/keywords_YYYY-MM-DD.csv` | Full keyword CSV |
| `reports/seo_report_YYYY-MM-DD.json` | Structured JSON |
| `reports/dashboard_YYYY-MM-DD.html` | HTML dashboard |
| `logs/seo_platform.log` | Rotating log file |

---

## GitHub Actions

The workflow at `.github/workflows/daily_run.yml`:
- Runs **every day at 03:00 UTC** (06:00 EAT)
- Installs dependencies
- Executes `python main.py run`
- Uploads reports and the database snapshot as workflow artifacts (90-day retention)
- Optionally commits reports back to the repository (set `COMMIT_REPORTS=true` in repository variables)

Add your API keys as **repository secrets** (`Settings → Secrets → Actions`):
`GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `OPENAI_API_KEY`

You can also trigger the pipeline manually via **Actions → Run workflow** and choose which step to run.

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full pipeline diagram and database schema.

---

## Project Structure

```
seo-intelligence-uganda/
├── main.py                          # CLI entry point
├── config.py                        # All configuration (reads from .env)
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
│
├── seo_intelligence/
│   ├── __init__.py
│   ├── logger.py                    # Centralised logging
│   ├── cache.py                     # Disk-backed TTL cache
│   ├── retry.py                     # Retry decorator
│   ├── database.py                  # SQLite schema + all DB helpers
│   ├── keyword_discovery.py         # Google Suggest + PAA + related searches
│   ├── google_trends_module.py      # pytrends integration (geo=UG)
│   ├── keyword_classifier.py        # Intent classification
│   ├── serp_analysis.py             # SERP fetching + SERP weakness scoring
│   ├── page_analysis.py             # Page content extraction
│   ├── competitor_tracker.py        # Domain visibility tracking
│   ├── content_gap.py               # Gap detection + recommendations
│   ├── opportunity_scorer.py        # Weighted 0–100 opportunity score
│   ├── content_brief.py             # Article brief generation
│   └── report_generator.py          # Markdown / CSV / JSON / HTML reports
│
├── tests/
│   ├── test_classifier.py
│   ├── test_database.py
│   └── test_opportunity_scorer.py
│
├── docs/
│   ├── architecture.md
│   └── quickstart.md
│
└── .github/
    └── workflows/
        └── daily_run.yml            # Daily GitHub Actions pipeline
```

---

## License

MIT — see [LICENSE](LICENSE).
