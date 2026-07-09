"""
Tests for the database layer.

Uses a temporary SQLite database so the real data/seo_intelligence.db
is never touched during tests.

Run with: pytest tests/test_database.py -v
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect DB_PATH to a temporary file for each test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("config.DB_PATH", db_file)
    monkeypatch.setattr("seo_intelligence.database.DB_PATH", db_file)

    from seo_intelligence.database import init_db
    init_db()
    yield db_file


class TestKeywords:
    def test_upsert_and_retrieve(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_keyword, get_all_keywords

        upsert_keyword("web design uganda", "2024-01-01", trend_score=75.0, source="test", intent="Local")
        rows = get_all_keywords()
        assert any(r["keyword"] == "web design uganda" for r in rows)

    def test_upsert_updates_on_conflict(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_keyword, get_keywords_by_date

        upsert_keyword("website", "2024-01-01", trend_score=10.0)
        upsert_keyword("website", "2024-01-01", trend_score=90.0)
        rows = get_keywords_by_date("2024-01-01")
        matching = [r for r in rows if r["keyword"] == "website"]
        assert len(matching) == 1
        assert matching[0]["trend_score"] == 90.0

    def test_get_keywords_by_date_filter(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_keyword, get_keywords_by_date

        upsert_keyword("seo kampala", "2024-06-01")
        upsert_keyword("seo kampala", "2024-07-01")
        rows = get_keywords_by_date("2024-06-01")
        assert all(r["date"] == "2024-06-01" for r in rows)


class TestSerpResults:
    def test_upsert_and_retrieve(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_serp_result, get_serp_results

        upsert_serp_result("web design", "2024-01-01", 1, "Title", "https://example.com", "example.com", "Snippet")
        rows = get_serp_results("web design")
        assert len(rows) >= 1
        assert rows[0]["url"] == "https://example.com"

    def test_get_serp_results_by_date(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_serp_result, get_serp_results

        upsert_serp_result("seo", "2024-01-01", 2, "T", "https://a.com", "a.com", "")
        upsert_serp_result("seo", "2024-02-01", 1, "T", "https://b.com", "b.com", "")
        rows = get_serp_results("seo", day="2024-01-01")
        assert all(r["date"] == "2024-01-01" for r in rows)


class TestPageAnalysis:
    def test_upsert_and_retrieve(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_page_analysis, get_page_analysis

        data = {
            "url": "https://example.com/about",
            "date": "2024-01-01",
            "domain": "example.com",
            "h1": "About us",
            "h2s": "Team|Services",
            "h3s": "",
            "word_count": 800,
            "image_count": 5,
            "table_count": 1,
            "faq_count": 3,
            "schema_types": "Article,FAQPage",
            "meta_description": "About our agency",
            "og_title": "About",
            "reading_time_min": 3.4,
            "last_modified": "",
            "content_quality_score": 65.0,
        }
        upsert_page_analysis(data)
        row = get_page_analysis("https://example.com/about")
        assert row is not None
        assert row["word_count"] == 800
        assert row["faq_count"] == 3


class TestCompetitors:
    def test_upsert_and_list(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_competitor, get_all_competitors

        upsert_competitor("isazeni.com", "2024-01-01", 50, 320.0)
        comps = get_all_competitors()
        assert any(c["domain"] == "isazeni.com" for c in comps)

    def test_competitor_history(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_competitor, get_competitor_history

        upsert_competitor("test.com", "2024-01-01", 10, 50.0)
        upsert_competitor("test.com", "2024-02-01", 15, 80.0)
        history = get_competitor_history("test.com")
        assert len(history) == 2
        assert history[0]["date"] < history[1]["date"]


class TestContentGaps:
    def test_upsert_and_retrieve(self, tmp_db: Path) -> None:
        from seo_intelligence.database import upsert_content_gap, get_content_gaps

        upsert_content_gap("Mobile Money", "2024-01-01", "mobile money website", "Write a guide")
        gaps = get_content_gaps()
        assert any(g["topic"] == "Mobile Money" for g in gaps)
