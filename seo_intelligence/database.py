"""
SQLite database layer.

The schema is created automatically on first run — no manual SQL setup required.
All public functions accept plain Python types and return dataclasses / dicts.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Generator

from config import DB_PATH
from seo_intelligence.logger import get_logger

log = get_logger(__name__)

# ── Schema ─────────────────────────────────────────────────────────────────────
_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS keywords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL,
    date            TEXT NOT NULL,
    trend_score     REAL DEFAULT 0,
    source          TEXT DEFAULT '',
    country         TEXT DEFAULT 'UG',
    intent          TEXT DEFAULT '',
    opportunity_score REAL DEFAULT 0,
    UNIQUE(keyword, date)
);

CREATE TABLE IF NOT EXISTS serp_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL,
    date            TEXT NOT NULL,
    position        INTEGER,
    title           TEXT,
    url             TEXT,
    domain          TEXT,
    snippet         TEXT,
    UNIQUE(keyword, date, url)
);

CREATE TABLE IF NOT EXISTS page_analysis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL,
    date            TEXT NOT NULL,
    domain          TEXT,
    h1              TEXT,
    h2s             TEXT,
    h3s             TEXT,
    word_count      INTEGER DEFAULT 0,
    image_count     INTEGER DEFAULT 0,
    table_count     INTEGER DEFAULT 0,
    faq_count       INTEGER DEFAULT 0,
    schema_types    TEXT,
    meta_description TEXT,
    og_title        TEXT,
    reading_time_min REAL DEFAULT 0,
    last_modified   TEXT,
    content_quality_score REAL DEFAULT 0,
    UNIQUE(url, date)
);

CREATE TABLE IF NOT EXISTS competitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT NOT NULL,
    date            TEXT NOT NULL,
    keyword_count   INTEGER DEFAULT 0,
    visibility_score REAL DEFAULT 0,
    UNIQUE(domain, date)
);

CREATE TABLE IF NOT EXISTS competitor_keywords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT NOT NULL,
    keyword         TEXT NOT NULL,
    position        INTEGER,
    date            TEXT NOT NULL,
    UNIQUE(domain, keyword, date)
);

CREATE TABLE IF NOT EXISTS content_gaps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    date            TEXT NOT NULL,
    keywords        TEXT,
    recommendation  TEXT,
    UNIQUE(topic, date)
);

CREATE TABLE IF NOT EXISTS content_briefs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL,
    date            TEXT NOT NULL,
    title           TEXT,
    meta_description TEXT,
    slug            TEXT,
    outline         TEXT,
    suggested_h2s   TEXT,
    suggested_faqs  TEXT,
    suggested_schema TEXT,
    suggested_internal_links TEXT,
    estimated_word_count INTEGER DEFAULT 0,
    UNIQUE(keyword, date)
);

CREATE INDEX IF NOT EXISTS idx_keywords_kw   ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_date ON keywords(date);
CREATE INDEX IF NOT EXISTS idx_serp_kw       ON serp_results(keyword);
CREATE INDEX IF NOT EXISTS idx_page_url      ON page_analysis(url);
CREATE INDEX IF NOT EXISTS idx_comp_domain   ON competitors(domain);
"""


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    with _conn() as con:
        con.executescript(_DDL)
    log.info("Database initialised at %s", DB_PATH)


# ── Keywords ───────────────────────────────────────────────────────────────────

def upsert_keyword(
    keyword: str,
    today: str,
    trend_score: float = 0.0,
    source: str = "",
    intent: str = "",
    opportunity_score: float = 0.0,
) -> None:
    sql = """
        INSERT INTO keywords (keyword, date, trend_score, source, intent, opportunity_score)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(keyword, date) DO UPDATE SET
            trend_score = excluded.trend_score,
            source = excluded.source,
            intent = excluded.intent,
            opportunity_score = excluded.opportunity_score
    """
    with _conn() as con:
        con.execute(sql, (keyword, today, trend_score, source, intent, opportunity_score))


def get_all_keywords(limit: int = 10000) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM keywords ORDER BY opportunity_score DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_keywords_by_date(day: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM keywords WHERE date = ? ORDER BY opportunity_score DESC", (day,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── SERP ───────────────────────────────────────────────────────────────────────

def upsert_serp_result(
    keyword: str,
    today: str,
    position: int,
    title: str,
    url: str,
    domain: str,
    snippet: str,
) -> None:
    sql = """
        INSERT INTO serp_results (keyword, date, position, title, url, domain, snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(keyword, date, url) DO UPDATE SET
            position = excluded.position,
            title = excluded.title,
            snippet = excluded.snippet
    """
    with _conn() as con:
        con.execute(sql, (keyword, today, position, title, url, domain, snippet))


def get_serp_results(keyword: str, day: str | None = None) -> list[dict]:
    with _conn() as con:
        if day:
            rows = con.execute(
                "SELECT * FROM serp_results WHERE keyword=? AND date=? ORDER BY position",
                (keyword, day),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM serp_results WHERE keyword=? ORDER BY date DESC, position",
                (keyword,),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Page analysis ──────────────────────────────────────────────────────────────

def upsert_page_analysis(data: dict) -> None:
    sql = """
        INSERT INTO page_analysis
            (url, date, domain, h1, h2s, h3s, word_count, image_count, table_count,
             faq_count, schema_types, meta_description, og_title, reading_time_min,
             last_modified, content_quality_score)
        VALUES
            (:url, :date, :domain, :h1, :h2s, :h3s, :word_count, :image_count,
             :table_count, :faq_count, :schema_types, :meta_description, :og_title,
             :reading_time_min, :last_modified, :content_quality_score)
        ON CONFLICT(url, date) DO UPDATE SET
            word_count = excluded.word_count,
            image_count = excluded.image_count,
            content_quality_score = excluded.content_quality_score
    """
    with _conn() as con:
        con.execute(sql, data)


def get_page_analysis(url: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM page_analysis WHERE url=? ORDER BY date DESC LIMIT 1", (url,)
        ).fetchone()
    return dict(row) if row else None


# ── Competitors ────────────────────────────────────────────────────────────────

def upsert_competitor(domain: str, today: str, keyword_count: int, visibility: float) -> None:
    sql = """
        INSERT INTO competitors (domain, date, keyword_count, visibility_score)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(domain, date) DO UPDATE SET
            keyword_count = excluded.keyword_count,
            visibility_score = excluded.visibility_score
    """
    with _conn() as con:
        con.execute(sql, (domain, today, keyword_count, visibility))


def upsert_competitor_keyword(domain: str, keyword: str, position: int, today: str) -> None:
    sql = """
        INSERT INTO competitor_keywords (domain, keyword, position, date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(domain, keyword, date) DO UPDATE SET position = excluded.position
    """
    with _conn() as con:
        con.execute(sql, (domain, keyword, position, today))


def get_competitor_history(domain: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM competitors WHERE domain=? ORDER BY date", (domain,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_competitors(day: str | None = None) -> list[dict]:
    with _conn() as con:
        if day:
            rows = con.execute(
                "SELECT * FROM competitors WHERE date=? ORDER BY visibility_score DESC", (day,)
            ).fetchall()
        else:
            # Return the single latest snapshot per domain (deterministic via subquery)
            rows = con.execute(
                """
                SELECT c.*
                FROM competitors c
                INNER JOIN (
                    SELECT domain, MAX(date) AS max_date
                    FROM competitors
                    GROUP BY domain
                ) latest ON c.domain = latest.domain AND c.date = latest.max_date
                ORDER BY c.visibility_score DESC
                """
            ).fetchall()
    return [dict(r) for r in rows]


def get_distinct_keywords_latest(limit: int = 10000) -> list[dict]:
    """
    Return one row per unique keyword — the most recent recorded row.

    Use this instead of ``get_all_keywords`` in pipeline commands that must
    process each keyword once without mixing historical duplicates.
    """
    with _conn() as con:
        rows = con.execute(
            """
            SELECT k.*
            FROM keywords k
            INNER JOIN (
                SELECT keyword, MAX(date) AS max_date
                FROM keywords
                GROUP BY keyword
            ) latest ON k.keyword = latest.keyword AND k.date = latest.max_date
            ORDER BY k.opportunity_score DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_serp_results_for_date(keyword: str, day: str) -> list[dict]:
    """Return SERP results for *keyword* on a specific *day*."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM serp_results WHERE keyword=? AND date=? ORDER BY position",
            (keyword, day),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Content gaps ───────────────────────────────────────────────────────────────

def upsert_content_gap(topic: str, today: str, keywords: str, recommendation: str) -> None:
    sql = """
        INSERT INTO content_gaps (topic, date, keywords, recommendation)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(topic, date) DO UPDATE SET
            keywords = excluded.keywords,
            recommendation = excluded.recommendation
    """
    with _conn() as con:
        con.execute(sql, (topic, today, keywords, recommendation))


def get_content_gaps(day: str | None = None) -> list[dict]:
    with _conn() as con:
        if day:
            rows = con.execute(
                "SELECT * FROM content_gaps WHERE date=?", (day,)
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM content_gaps ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


# ── Content briefs ─────────────────────────────────────────────────────────────

def upsert_content_brief(data: dict) -> None:
    sql = """
        INSERT INTO content_briefs
            (keyword, date, title, meta_description, slug, outline,
             suggested_h2s, suggested_faqs, suggested_schema,
             suggested_internal_links, estimated_word_count)
        VALUES
            (:keyword, :date, :title, :meta_description, :slug, :outline,
             :suggested_h2s, :suggested_faqs, :suggested_schema,
             :suggested_internal_links, :estimated_word_count)
        ON CONFLICT(keyword, date) DO UPDATE SET
            title = excluded.title,
            outline = excluded.outline
    """
    with _conn() as con:
        con.execute(sql, data)


def get_content_brief(keyword: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM content_briefs WHERE keyword=? ORDER BY date DESC LIMIT 1",
            (keyword,),
        ).fetchone()
    return dict(row) if row else None
