"""
Tests for the keyword intent classifier.

Run with: pytest tests/test_classifier.py -v
"""

import pytest

from seo_intelligence.keyword_classifier import Intent, classify, classify_many


class TestClassify:
    """Unit tests for :func:`classify`."""

    # ── Question ──────────────────────────────────────────────────────────────
    def test_question_what(self) -> None:
        result = classify("what is web design")
        assert result.intent == Intent.QUESTION

    def test_question_how(self) -> None:
        result = classify("how much does a website cost in Uganda")
        assert result.intent == Intent.QUESTION

    def test_question_mark(self) -> None:
        result = classify("is wordpress good for ecommerce?")
        assert result.intent == Intent.QUESTION

    # ── Transactional ─────────────────────────────────────────────────────────
    def test_transactional_buy(self) -> None:
        result = classify("buy website design Uganda")
        assert result.intent == Intent.TRANSACTIONAL

    def test_transactional_hire(self) -> None:
        result = classify("hire web designer Kampala")
        assert result.intent == Intent.TRANSACTIONAL

    def test_transactional_pricing(self) -> None:
        result = classify("website pricing packages Uganda")
        assert result.intent == Intent.TRANSACTIONAL

    # ── Local ─────────────────────────────────────────────────────────────────
    def test_local_uganda(self) -> None:
        result = classify("web design company Uganda")
        assert result.intent == Intent.LOCAL

    def test_local_kampala(self) -> None:
        result = classify("website developers Kampala")
        assert result.intent == Intent.LOCAL

    # ── Commercial ────────────────────────────────────────────────────────────
    def test_commercial_best(self) -> None:
        result = classify("best web design companies")
        assert result.intent == Intent.COMMERCIAL

    def test_commercial_compare(self) -> None:
        result = classify("wordpress vs wix comparison")
        assert result.intent == Intent.COMMERCIAL

    # ── Informational ─────────────────────────────────────────────────────────
    def test_informational_default(self) -> None:
        result = classify("website design")
        assert result.intent == Intent.INFORMATIONAL

    def test_informational_guide(self) -> None:
        result = classify("web design guide")
        assert result.intent == Intent.INFORMATIONAL

    # ── Confidence ───────────────────────────────────────────────────────────
    def test_confidence_range(self) -> None:
        result = classify("ecommerce website Uganda")
        assert 0.0 <= result.confidence <= 1.0

    # ── Signals ──────────────────────────────────────────────────────────────
    def test_signals_not_empty(self) -> None:
        result = classify("web designer")
        assert len(result.signals) > 0

    # ── classify_many ─────────────────────────────────────────────────────────
    def test_classify_many_length(self) -> None:
        keywords = ["web design", "buy website Uganda", "how to make a website"]
        results = classify_many(keywords)
        assert len(results) == len(keywords)

    def test_classify_many_preserves_order(self) -> None:
        keywords = ["informational keyword", "buy something Uganda"]
        results = classify_many(keywords)
        assert results[0].keyword == keywords[0]
        assert results[1].keyword == keywords[1]

    def test_empty_string(self) -> None:
        result = classify("")
        assert result.intent in Intent.__members__.values()
