"""
Central configuration for the SEO Intelligence Platform.

Values are loaded from environment variables with sensible defaults.
Copy .env.example to .env and fill in your credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
CACHE_DIR = BASE_DIR / ".cache"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "seo_intelligence.db"

for _d in (DATA_DIR, REPORTS_DIR, CACHE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Target geography ───────────────────────────────────────────────────────────
GEO = "UG"
LANGUAGE = "en"
COUNTRY_NAME = "Uganda"

# ── Seed topics ────────────────────────────────────────────────────────────────
SEED_KEYWORDS: list[str] = [
    "website",
    "website design",
    "web design",
    "web designer",
    "website development",
    "wordpress",
    "wordpress uganda",
    "website cost",
    "website pricing",
    "website maintenance",
    "website hosting",
    "domain registration",
    "SEO",
    "ecommerce website",
    "online shop",
    "school website",
    "church website",
    "NGO website",
    "company website",
    "business website",
    "landing page",
    "portfolio website",
    "government website",
    "restaurant website",
    "hotel website",
    "law firm website",
    "construction company website",
    "medical website",
    "digital marketing",
    "UI UX",
    "graphic design",
]

# ── Known competitors ──────────────────────────────────────────────────────────
KNOWN_COMPETITORS: list[str] = [
    "isazeni.com",
    "trophydevelopers.com",
    "armgenius.com",
    "webstaruganda.com",
]

# ── Google Custom Search API ───────────────────────────────────────────────────
GOOGLE_CSE_API_KEY: str = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")

# ── DataForSEO (optional premium SERP data) ────────────────────────────────────
DATAFORSEO_LOGIN: str = os.getenv("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD: str = os.getenv("DATAFORSEO_PASSWORD", "")

# ── OpenAI (for content briefs) ────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── HTTP / scraping ────────────────────────────────────────────────────────────
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF: float = float(os.getenv("RETRY_BACKOFF", "2.0"))
RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "1.5"))

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ── Cache ──────────────────────────────────────────────────────────────────────
CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))

# ── Google Trends ──────────────────────────────────────────────────────────────
TRENDS_TIMEFRAME: str = os.getenv("TRENDS_TIMEFRAME", "today 3-m")

# ── Autocomplete expansion ─────────────────────────────────────────────────────
ALPHABET: list[str] = list("abcdefghijklmnopqrstuvwxyz")
EXPAND_ALPHABET: bool = os.getenv("EXPAND_ALPHABET", "true").lower() == "true"

# ── SERP ───────────────────────────────────────────────────────────────────────
SERP_RESULTS_PER_PAGE: int = int(os.getenv("SERP_RESULTS_PER_PAGE", "10"))

# ── Opportunity scoring weights ────────────────────────────────────────────────
SCORE_WEIGHT_TREND: float = 0.25
SCORE_WEIGHT_INTENT: float = 0.20
SCORE_WEIGHT_COMPETITION: float = 0.25
SCORE_WEIGHT_CONTENT_QUALITY: float = 0.15
SCORE_WEIGHT_SERP_WEAKNESS: float = 0.15

# ── Commit reports back to repo (GitHub Actions) ───────────────────────────────
COMMIT_REPORTS: bool = os.getenv("COMMIT_REPORTS", "false").lower() == "true"
