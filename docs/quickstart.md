# Quick Start Guide

## Prerequisites

- Python 3.12+
- pip

## Installation

```bash
git clone https://github.com/your-org/seo-intelligence-uganda.git
cd seo-intelligence-uganda

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# or .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## First Run (no API keys required)

```bash
python main.py run
```

This will:
1. Discover keywords from Google Suggest (free)
2. Fetch Google Trends data (free via pytrends)
3. Classify keyword intent (rule-based, no API)
4. Scrape Google SERPs (free, rate-limited)
5. Analyse ranking pages
6. Track competitors
7. Identify content gaps
8. Score opportunities
9. Generate content briefs
10. Write reports to `reports/`

## With API Keys (recommended for production)

1. Copy `.env.example` to `.env`
2. Add your credentials:

```env
GOOGLE_CSE_API_KEY=your_key_here
GOOGLE_CSE_ID=your_cx_here
```

Google Custom Search gives you 100 free queries/day, which is enough for
a focused daily run on ~100 high-priority keywords.

## Running Individual Steps

```bash
python main.py discover     # ~10–20 minutes for full alphabet expansion
python main.py trends       # ~5 minutes
python main.py serp         # varies by keyword count
python main.py reports      # instant — reads from DB
```

## Viewing Results

Open the HTML dashboard:

```bash
open reports/dashboard_$(date +%Y-%m-%d).html
```

Or query the database directly:

```bash
sqlite3 data/seo_intelligence.db \
  "SELECT keyword, intent, trend_score, opportunity_score \
   FROM keywords ORDER BY opportunity_score DESC LIMIT 20;"
```

## GitHub Actions Setup

1. Push this repository to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add repository secrets:
   - `GOOGLE_CSE_API_KEY`
   - `GOOGLE_CSE_ID`
   - `OPENAI_API_KEY` (optional)
4. The pipeline runs automatically every day at 03:00 UTC
5. Download reports from the **Actions → Artifacts** section

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Too many requests` from Google Trends | Increase `RATE_LIMIT_DELAY` in `.env` |
| SERP scraping returns 0 results | Add `GOOGLE_CSE_API_KEY` — Google blocks scrapers |
| OpenAI briefs not generated | Set `OPENAI_API_KEY` in `.env` |
| Database locked | Only run one pipeline instance at a time |
