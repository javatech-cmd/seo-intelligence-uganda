# Architecture Overview

## Pipeline Flow

```
SEED_KEYWORDS
     │
     ▼
┌─────────────────────┐
│  keyword_discovery  │  Google Suggest + alphabet expansion + PAA
└─────────────────────┘
     │ all discovered keywords
     ▼
┌──────────────────────────┐
│  google_trends_module    │  pytrends interest-over-time scores (UG)
└──────────────────────────┘
     │ trend_score per keyword
     ▼
┌──────────────────────┐
│  keyword_classifier  │  Rule-based intent classification
└──────────────────────┘
     │ intent per keyword
     ▼
┌──────────────────┐
│  serp_analysis   │  CSE API → DataForSEO → HTML scraping fallback
└──────────────────┘
     │ top-10 URLs per keyword
     ▼
┌─────────────────┐
│  page_analysis  │  H1/H2/H3, word count, schema, FAQs, quality score
└─────────────────┘
     │ page features
     ▼
┌─────────────────────────┐
│  competitor_tracker     │  Domain visibility, keyword count, ranking deltas
└─────────────────────────┘
     │
     ▼
┌───────────────────────┐
│  content_gap          │  Compare heading coverage, generate recommendations
└───────────────────────┘
     │
     ▼
┌─────────────────────────┐
│  opportunity_scorer     │  Weighted score 0–100
└─────────────────────────┘
     │
     ▼
┌─────────────────┐
│  content_brief  │  Rule-based + optional OpenAI enrichment
└─────────────────┘
     │
     ▼
┌────────────────────┐
│  report_generator  │  Markdown · CSV · JSON · HTML dashboard
└────────────────────┘
```

## Database Schema

All tables are in `data/seo_intelligence.db` (SQLite, WAL mode).

| Table                | Description                                      |
|----------------------|--------------------------------------------------|
| `keywords`           | One row per keyword per day; stores scores       |
| `serp_results`       | Top-10 results per keyword per day               |
| `page_analysis`      | Detailed page features per URL per day           |
| `competitors`        | Visibility metrics per domain per day            |
| `competitor_keywords`| Individual keyword rankings per domain           |
| `content_gaps`       | Identified topic gaps with recommendations       |
| `content_briefs`     | Generated article briefs per keyword             |

## Configuration

All configuration lives in `config.py` and reads from `.env`.
See `.env.example` for the full list of supported variables.

## SERP Data Sources (priority order)

1. **Google Custom Search JSON API** — accurate, quota-limited (100 free queries/day)
2. **DataForSEO** — premium, no quota for paid accounts
3. **HTML scraping** — free, fragile, rate-limited

Set `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` in `.env` to use source 1.
Set `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` to use source 2.
Without either, source 3 is used automatically.
